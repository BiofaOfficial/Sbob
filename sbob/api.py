"""API REST, frontend compilato e worker in un solo processo."""

import asyncio
import json
import os
import shutil
import signal
import threading
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote, urlsplit

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__, config, db, engines, profili, prompts_studio
from .export import anki, markdown, pdf
from .pipeline import acquisizione, fasi
from .worker import Worker

STATIC = Path(__file__).parent / "static"
HOST_LOCALI = {"127.0.0.1", "localhost", "::1"}
PRODOTTI = ["prodotto", "dispensa", "mappa", "flashcard", "autoverifica", "glossario", "trascritto", "tutto"]


def _locale(valore: str) -> bool:
    """True se un header Host oppure Origin indica questo computer (la porta non conta)."""
    try:
        return urlsplit(valore if "://" in valore else f"//{valore}").hostname in HOST_LOCALI
    except ValueError:
        return False


def _intero(valore: str, campo: str) -> int:
    try:
        return int(valore)
    except ValueError:
        raise HTTPException(400, f"Valore non valido per {campo}") from None


def crea_app(cfg: dict | None = None, motori=None) -> FastAPI:
    cfg = cfg or config.carica()
    db.migra()
    motori = motori or engines.crea(cfg, config.motori_effettivi(cfg))
    worker = Worker(motori, cfg)

    @asynccontextmanager
    async def vita(app):
        worker.avvia()
        yield
        await worker.ferma()

    app = FastAPI(title="Sbob", version=__version__, lifespan=vita)
    app.state.worker, app.state.motori, app.state.cfg = worker, motori, cfg

    @app.middleware("http")
    async def solo_locale(request: Request, call_next):
        """Sbob non ha login: lo protegge il rispondere solo a questo computer.

        Host diverso da localhost = DNS rebinding; Origin esterna = un'altra pagina web
        che prova a comandare Sbob (CSRF). In entrambi i casi la richiesta è rifiutata.
        """
        origin = request.headers.get("origin")
        if not _locale(request.headers.get("host", "")) or (origin is not None and not _locale(origin)):
            return JSONResponse({"detail": "Richiesta non locale rifiutata"}, status_code=403)
        return await call_next(request)

    def _ferma_processo():
        os.kill(os.getpid(), signal.SIGINT)  # uvicorn chiude in ordine: worker fermato, caffeinate spento

    app.state.ferma = _ferma_processo

    @app.post("/api/esci")
    def esci():
        """Chiude Sbob. Le fasi interrotte ripartono al prossimo avvio."""
        threading.Timer(0.5, lambda: app.state.ferma()).start()
        return {"ok": True}

    MSG_TOKEN = "Per separare le voci serve il token Hugging Face: inseriscilo in Impostazioni"  # noqa: S105

    def voci_disponibili() -> bool:
        return bool(cfg.get("hf_token")) or motori.nome == "fake"

    def in_coda(lid: str, nome: str) -> None:
        """Rimette in coda una fase con tutti i controlli: token per le voci, fase già in corso."""
        lav = db.lavoro(lid)
        if lav["voci_attive"] and not voci_disponibili() and (nome == "voci" or "voci" in fasi.dipendenti(nome)):
            stati = {f["nome"]: f["stato"] for f in db.fasi(lid)}
            if nome == "voci" or stati.get("voci") in ("fatto", "errore"):
                raise HTTPException(400, MSG_TOKEN)
        try:
            fasi.rimetti_in_coda(lid, nome)
        except ValueError:
            raise HTTPException(409, "Questa parte del lavoro è in corso: riprova quando ha finito") from None

    def trova(lid: str) -> dict:
        lav = db.lavoro(lid)
        if lav is None:
            raise HTTPException(404, "Lavoro non trovato")
        return lav

    # ── profili e stato ──────────────────────────────────────
    @app.get("/api/profili")
    def get_profili():
        return {"default": profili.PROFILO_DEFAULT, "profili": profili.per_api()}

    @app.get("/api/stato")
    def get_stato():
        out = {"versione": __version__, "motori": motori.nome, "cartella_dati": str(config.home()),
               "ffmpeg": shutil.which("ffmpeg") is not None}
        for k in ("trascrittore", "separatore", "llm"):
            f = getattr(getattr(motori, k), "stato", None)
            out[k] = f() if f else {"finto": True}
        out["modelli"] = {
            "llm": {"nome": cfg["llm_modello"], "stato": _stato_modello("llm", out["llm"])},
            "whisper": {"nome": cfg["whisper_modello"], "stato": _stato_modello("trascrittore", out["trascrittore"])},
        }
        out["ctx"] = int(cfg["llm_ctx"])
        out["hf_token"] = bool(cfg.get("hf_token"))
        return out

    def _stato_modello(motore: str, s: dict) -> str:
        """UP = al lavoro; WARM = in memoria; COLD = installato, non caricato; DOWN = non disponibile."""
        if worker.in_uso == motore:
            return "UP"
        if s.get("finto"):
            return "WARM"
        if motore == "llm":
            if not (s.get("raggiungibile") and s.get("modello_presente")):
                return "DOWN"
        elif not (s.get("installato") and s.get("scaricato")):
            return "DOWN"
        return "WARM" if s.get("caricato") else "COLD"

    @app.post("/api/riscalda")
    async def riscalda():
        errori = []
        for k in ("trascrittore", "llm"):
            f = getattr(getattr(motori, k), "riscalda", None)
            if f and worker.in_uso != k:
                try:
                    await asyncio.to_thread(f)
                except Exception as e:
                    errori.append(str(e))
        if errori:
            raise HTTPException(503, "; ".join(errori))
        return get_stato()

    # ── impostazioni ─────────────────────────────────────────
    class Impostazioni(BaseModel):
        lingua_ui: str | None = None
        whisper_modello: str | None = None
        llm_modello: str | None = None
        llm_ctx: int | None = Field(None, ge=1024)
        hf_token: str | None = None
        vocabolario_globale: str | None = None

    @app.get("/api/impostazioni")
    def get_impostazioni():
        out = {k: v for k, v in cfg.items() if k != "hf_token"}
        out["hf_token_impostato"] = bool(cfg.get("hf_token"))
        return out

    @app.put("/api/impostazioni")
    def put_impostazioni(i: Impostazioni):
        for k, v in i.model_dump(exclude_none=True).items():
            cfg[k] = v.strip() if isinstance(v, str) else v
        if hasattr(motori.trascrittore, "modello"):
            motori.trascrittore.modello = cfg["whisper_modello"]
        if hasattr(motori.llm, "modello"):
            motori.llm.modello, motori.llm.ctx = cfg["llm_modello"], int(cfg["llm_ctx"])
        config.salva(cfg)
        return get_impostazioni()

    # ── corsi ────────────────────────────────────────────────
    class Corso(BaseModel):
        nome: str
        vocabolario: str = ""

    @app.get("/api/corsi")
    def get_corsi():
        return db.righe("SELECT c.*, (SELECT COUNT(*) FROM lavori l WHERE l.corso_id=c.id) AS n_lavori "
                        "FROM corsi c ORDER BY c.nome COLLATE NOCASE")

    @app.post("/api/corsi")
    def post_corso(c: Corso):
        if not c.nome.strip():
            raise HTTPException(400, "Il nome del corso è obbligatorio")
        if db.riga("SELECT id FROM corsi WHERE nome=?", c.nome.strip()):
            raise HTTPException(409, "Esiste già un corso con questo nome")
        cid = db.esegui("INSERT INTO corsi(nome, vocabolario, creato) VALUES(?,?,?)",
                        c.nome.strip(), c.vocabolario, db.adesso())
        return db.riga("SELECT * FROM corsi WHERE id=?", cid)

    @app.put("/api/corsi/{cid}")
    def put_corso(cid: int, c: Corso):
        if not c.nome.strip():
            raise HTTPException(400, "Il nome del corso è obbligatorio")
        if db.riga("SELECT id FROM corsi WHERE id=?", cid) is None:
            raise HTTPException(404, "Corso non trovato")
        if db.riga("SELECT id FROM corsi WHERE nome=? AND id<>?", c.nome.strip(), cid):
            raise HTTPException(409, "Esiste già un corso con questo nome")
        db.esegui("UPDATE corsi SET nome=?, vocabolario=? WHERE id=?", c.nome.strip(), c.vocabolario, cid)
        return db.riga("SELECT * FROM corsi WHERE id=?", cid)

    @app.delete("/api/corsi/{cid}")
    def delete_corso(cid: int):
        db.esegui("DELETE FROM corsi WHERE id=?", cid)
        return {"ok": True}

    # ── lavori ───────────────────────────────────────────────
    @app.post("/api/lavori")
    def post_lavoro(
        file: UploadFile | None = File(None), url: str = Form(""), titolo: str = Form(""),
        profilo: str = Form(profili.PROFILO_DEFAULT), corso_id: str = Form(""), lingua: str = Form("auto"),
        lingua_prodotti: str = Form("auto"), voci_attive: str = Form(""), termini_extra: str = Form(""),
        parti: str = Form("[]"),
    ):
        if profilo not in profili.PROFILI:
            raise HTTPException(400, "Profilo sconosciuto")
        url = url.strip()
        if not url and (file is None or not file.filename):
            raise HTTPException(400, "Serve un file o un URL")
        if url and not url.lower().startswith(("http://", "https://")):
            raise HTTPException(400, "L'URL deve iniziare con http:// o https://")
        lid = uuid.uuid4().hex[:12]
        cart = fasi.cartella(lid)
        nome_file = None
        if not url:
            est = Path(file.filename).suffix.lower()
            if est not in acquisizione.ESTENSIONI:
                shutil.rmtree(cart, ignore_errors=True)
                raise HTTPException(400, f"Formato non supportato: {est or 'sconosciuto'}")
            nome_file = "sorgente" + est
            with (cart / nome_file).open("wb") as out:
                shutil.copyfileobj(file.file, out, 1024 * 1024)
        voci = (voci_attive.lower() in ("1", "true", "on", "si", "sì")) if voci_attive else \
            (profili.profilo(profilo)["voci_default"] and voci_disponibili())
        if voci and not voci_disponibili():
            shutil.rmtree(cart, ignore_errors=True)
            raise HTTPException(400, MSG_TOKEN)
        sorgente = url or file.filename
        db.esegui(
            "INSERT INTO lavori(id, titolo, corso_id, profilo, sorgente_tipo, sorgente, file_sorgente, lingua, "
            "lingua_prodotti, voci_attive, termini_extra, parti_json, creato) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            lid, titolo.strip() or (url or Path(file.filename).stem), _intero(corso_id, "corso_id") if corso_id else None,
            profilo, "url" if url else "file", sorgente, nome_file, lingua or "auto", lingua_prodotti or "auto",
            int(voci), termini_extra, json.dumps(db.json_campo(parti, [])), db.adesso(),
        )
        fasi.crea_fasi(lid, profilo, voci)
        worker.sveglia()
        return dettaglio(lid)

    @app.get("/api/lavori")
    def get_lavori(corso: str = "", profilo: str = "", stato: str = ""):
        sql, args = "SELECT l.*, c.nome AS corso FROM lavori l LEFT JOIN corsi c ON c.id=l.corso_id WHERE 1=1", []
        if corso == "nessuno":
            sql += " AND l.corso_id IS NULL"
        elif corso:
            sql += " AND l.corso_id=?"
            args.append(_intero(corso, "corso"))
        if profilo:
            sql += " AND l.profilo=?"
            args.append(profilo)
        out = []
        for lav in db.righe(sql + " ORDER BY l.creato DESC", *args):
            lav["fasi"] = db.fasi(lav["id"])
            lav["stato"] = stato_sintetico(lav["fasi"])
            if not stato or stato == lav["stato"] or (stato == "attivi" and lav["stato"] in ("corso", "coda")):
                out.append(lav)
        return out

    def stato_sintetico(fs: list[dict]) -> str:
        stati = {f["stato"] for f in fs}
        if "errore" in stati:
            return "errore"
        if "corso" in stati:
            return "corso"
        if "coda" in stati:
            return "coda"
        return "fatto"

    @app.get("/api/lavori/{lid}")
    def dettaglio(lid: str):
        lav = trova(lid)
        lav["meta"] = db.json_campo(lav.pop("meta_json"), {})
        lav["parti"] = db.json_campo(lav.pop("parti_json"), [])
        lav["fasi"] = db.fasi(lid)
        lav["stato"] = stato_sintetico(lav["fasi"])
        lav["voci"] = db.voci(lid)
        lav["corso"] = (db.riga("SELECT nome FROM corsi WHERE id=?", lav["corso_id"]) or {}).get("nome") \
            if lav["corso_id"] else None
        lav["lingua_effettiva"] = fasi.lingua_prodotti(lav | {"parti_json": "[]"})
        etichetta = fasi.etichettatore(trova(lid))
        lav["segmenti"] = [s | {"nome_voce": etichetta(s["voce"])} for s in db.segmenti(lid)]
        prodotti = {}
        for r in db.righe("SELECT tipo, contenuto, aggiornato FROM prodotti WHERE lavoro_id=?", lid):
            if r["tipo"] == "note":
                continue
            prodotti[r["tipo"]] = {"contenuto": r["contenuto"] if r["tipo"] in ("prodotto", "mappa", "dispensa")
                                   else json.loads(r["contenuto"]), "aggiornato": r["aggiornato"]}
        lav["prodotti"] = prodotti
        lav["vocabolario"] = fasi.vocabolario(lav)
        lav["voci_disponibili"] = voci_disponibili()
        lav["audio"] = (fasi.cartella(lid) / "audio.m4a").is_file() and \
            any(f["nome"] == "audio" and f["stato"] == "fatto" for f in lav["fasi"])
        return lav

    class Modifica(BaseModel):
        titolo: str | None = None
        corso_id: int | None = None
        senza_corso: bool = False
        voci_attive: bool | None = None
        lingua: str | None = None
        lingua_prodotti: str | None = None
        parti: list[str] | None = None

    @app.patch("/api/lavori/{lid}")
    def patch_lavoro(lid: str, m: Modifica):
        lav = trova(lid)
        campi: dict = {}
        if m.titolo is not None and m.titolo.strip():
            campi["titolo"] = m.titolo.strip()
        if m.senza_corso:
            campi["corso_id"] = None
        elif m.corso_id is not None:
            campi["corso_id"] = m.corso_id
        db.aggiorna_lavoro(lid, **campi)
        if m.voci_attive is not None and bool(m.voci_attive) != bool(lav["voci_attive"]):
            if m.voci_attive and not voci_disponibili():
                raise HTTPException(400, MSG_TOKEN)
            if any(f["nome"] == "voci" and f["stato"] == "corso" for f in db.fasi(lid)):
                raise HTTPException(409, "La separazione delle voci è in corso: riprova quando ha finito")
            db.aggiorna_lavoro(lid, voci_attive=int(m.voci_attive))
            in_coda(lid, "voci")
        if m.lingua is not None and m.lingua != lav["lingua"]:
            # lingua sbagliata (es. rilevata male da whisper): si rifà la trascrizione e tutto ciò che segue
            if any(f["nome"] == "trascrizione" and f["stato"] == "corso" for f in db.fasi(lid)):
                raise HTTPException(409, "La trascrizione è in corso: riprova quando ha finito")
            db.aggiorna_lavoro(lid, lingua=m.lingua or "auto", lingua_rilevata=None)
            in_coda(lid, "trascrizione")
        if m.lingua_prodotti is not None and m.lingua_prodotti != lav["lingua_prodotti"]:
            db.aggiorna_lavoro(lid, lingua_prodotti=m.lingua_prodotti)
            in_coda(lid, "note")
        if m.parti is not None:
            db.aggiorna_lavoro(lid, parti_json=json.dumps(m.parti[:2], ensure_ascii=False))
            in_coda(lid, "note")
        worker.sveglia()
        return dettaglio(lid)

    class Voce(BaseModel):
        etichetta: str
        nome: str = ""
        parte: str = ""

    @app.put("/api/lavori/{lid}/voci")
    def put_voci(lid: str, vs: list[Voce]):
        trova(lid)
        for v in vs:
            db.esegui("UPDATE voci SET nome=?, parte=? WHERE lavoro_id=? AND etichetta=?",
                      v.nome.strip(), v.parte.strip(), lid, v.etichetta)
        # rinominare una voce rigenera solo i prodotti, non la trascrizione
        stati = {f["nome"]: f["stato"] for f in db.fasi(lid)}
        if stati.get("note") in ("fatto", "errore"):
            in_coda(lid, "note")
        worker.sveglia()
        return dettaglio(lid)

    class Esclusione(BaseModel):
        indici: list[int]
        escluso: bool

    @app.put("/api/lavori/{lid}/segmenti")
    def escludi_segmenti(lid: str, e: Esclusione):
        trova(lid)
        with db.connetti() as c:
            c.executemany("UPDATE segmenti SET escluso=? WHERE lavoro_id=? AND indice=?",
                          [(int(e.escluso), lid, i) for i in e.indici])
        stati = {f["nome"]: f["stato"] for f in db.fasi(lid)}
        if stati.get("note") in ("fatto", "errore"):
            db.aggiorna_lavoro(lid, trascritto_modificato=1)
        return dettaglio(lid)

    class Termini(BaseModel):
        termini: list[str]

    @app.post("/api/lavori/{lid}/vocabolario")
    def aggiungi_vocabolario(lid: str, t: Termini):
        """Termini del glossario → vocabolario del corso (o globale): aiutano le trascrizioni successive."""
        lav = trova(lid)
        if lav["corso_id"]:
            corso = db.riga("SELECT vocabolario FROM corsi WHERE id=?", lav["corso_id"])
            attuali = fasi.termini(corso["vocabolario"])
        else:
            attuali = fasi.termini(cfg.get("vocabolario_globale", ""))
        nuovi = [x.strip() for x in t.termini if x.strip() and x.strip().lower() not in {a.lower() for a in attuali}]
        testo = "\n".join(attuali + nuovi)
        if lav["corso_id"]:
            db.esegui("UPDATE corsi SET vocabolario=? WHERE id=?", testo, lav["corso_id"])
        else:
            cfg["vocabolario_globale"] = testo
            config.salva(cfg)
        return {"vocabolario": attuali + nuovi, "dove": "corso" if lav["corso_id"] else "globale"}

    @app.post("/api/lavori/{lid}/fasi/{nome}/riprova")
    def riprova(lid: str, nome: str):
        trova(lid)
        if nome not in fasi.NOMI:
            raise HTTPException(404, "Fase sconosciuta")
        in_coda(lid, nome)
        worker.sveglia()
        return dettaglio(lid)

    @app.post("/api/lavori/{lid}/studio")
    def genera_studio(lid: str):
        trova(lid)
        for f in db.fasi(lid):
            if f["nome"] in fasi.STUDIO and f["stato"] in ("manuale", "errore"):
                in_coda(lid, f["nome"])
        worker.sveglia()
        return dettaglio(lid)

    class Dispensa(BaseModel):
        livello: str = "sintetica"

    @app.post("/api/lavori/{lid}/dispensa")
    def genera_dispensa(lid: str, m: Dispensa):
        trova(lid)
        if m.livello not in prompts_studio.LIVELLI:
            raise HTTPException(400, "Livello di sintesi sconosciuto")
        db.aggiorna_lavoro(lid, dispensa_livello=m.livello)
        in_coda(lid, "dispensa")
        worker.sveglia()
        return dettaglio(lid)

    @app.delete("/api/lavori/{lid}")
    def delete_lavoro(lid: str):
        trova(lid)
        fasi.elimina_lavoro(lid)
        return {"ok": True}

    @app.get("/api/lavori/{lid}/audio")
    def audio(lid: str):
        trova(lid)
        p = fasi.cartella(lid) / "audio.m4a"
        if not p.is_file():
            raise HTTPException(404, "Audio non ancora pronto")
        return FileResponse(p, media_type="audio/mp4")

    @app.get("/api/lavori/{lid}/export/{tipo}.{formato}")
    def export(lid: str, tipo: str, formato: str):
        lav = trova(lid)
        if tipo not in PRODOTTI:
            raise HTTPException(404, "Prodotto sconosciuto")
        base = "".join(ch if ch.isalnum() or ch in " -_" else "_" for ch in lav["titolo"])[:80].strip() or "sbob"
        nome = f"{base} - {markdown.titolo_prodotto(lav, tipo)}"
        try:
            if formato == "md":
                return PlainTextResponse(markdown.documento(lav, tipo), media_type="text/markdown; charset=utf-8",
                                         headers=_scarica(f"{nome}.md"))
            if formato == "pdf" and tipo != "mappa":
                return Response(pdf.documento(lav, tipo), media_type="application/pdf",
                                headers=_scarica(f"{nome}.pdf"))
            if formato == "txt" and tipo == "flashcard":
                return PlainTextResponse(anki.tsv(lid), headers=_scarica(f"{nome} (Anki).txt"))
        except (KeyError, TypeError):
            raise HTTPException(404, "Prodotto non ancora generato") from None
        raise HTTPException(400, "Formato non disponibile per questo prodotto")

    # ── frontend compilato ───────────────────────────────────
    if (STATIC / "index.html").is_file():
        if (STATIC / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=STATIC / "assets"), name="assets")

        @app.get("/{percorso:path}", include_in_schema=False)
        def spa(percorso: str):
            f = STATIC / percorso
            if percorso and f.is_file() and STATIC in f.resolve().parents:
                return FileResponse(f)
            return FileResponse(STATIC / "index.html")

    return app


def _scarica(nome: str) -> dict:
    return {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(nome)}"}
