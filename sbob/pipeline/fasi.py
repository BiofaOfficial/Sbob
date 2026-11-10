"""Fasi rieseguibili della pipeline e loro dipendenze."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from pydantic import ValidationError

from .. import config, db, profili, prompts_studio
from . import acquisizione, mapreduce

# nome → (dipende da, motore usato)
FASI: list[tuple[str, list[str], str | None]] = [
    ("acquisizione", [], None),
    ("audio", ["acquisizione"], None),
    ("trascrizione", ["audio"], "trascrittore"),
    ("voci", ["trascrizione"], "separatore"),
    ("note", ["voci"], "llm"),
    ("prodotto", ["note"], "llm"),
    ("mappa", ["note"], "llm"),
    ("flashcard", ["note"], "llm"),
    ("autoverifica", ["note"], "llm"),
    ("glossario", ["note"], "llm"),
    ("dispensa", ["note"], "llm"),  # su richiesta, con livello di sintesi
]
NOMI = [f[0] for f in FASI]
DIPENDENZE = {n: d for n, d, _ in FASI}
MOTORE = {n: m for n, _, m in FASI}
STUDIO = ["mappa", "flashcard", "autoverifica", "glossario"]


def _antenati(nome: str) -> set[str]:
    out: set[str] = set()
    for d in DIPENDENZE[nome]:
        out |= {d} | _antenati(d)
    return out


# una fase parte solo se TUTTE le fasi a monte sono fatte o saltate
ANTENATI = {n: _antenati(n) for n in NOMI}


def cartella(lid: str) -> Path:
    p = config.home() / "lavori" / lid
    p.mkdir(parents=True, exist_ok=True)
    return p


def crea_fasi(lid: str, profilo: str, voci_attive: bool) -> None:
    auto = profili.profilo(profilo)["studio_auto"]
    with db.connetti() as c:
        for i, n in enumerate(NOMI):
            stato = "coda"
            if n == "voci" and not voci_attive:
                stato = "saltata"
            elif (n in STUDIO and not auto) or n == "dispensa":
                stato = "manuale"
            c.execute("INSERT INTO fasi(lavoro_id, nome, ordine, stato) VALUES(?,?,?,?)", (lid, n, i, stato))


def dipendenti(nome: str) -> list[str]:
    out, frontiera = [], [nome]
    while frontiera:
        x = frontiera.pop()
        for n, deps in DIPENDENZE.items():
            if x in deps and n not in out:
                out.append(n)
                frontiera.append(n)
    return out


def rimetti_in_coda(lid: str, nome: str) -> None:
    """Rimette in coda una fase e quelle già eseguite che ne dipendono."""
    lav = db.lavoro(lid)
    stati = {f["nome"]: f["stato"] for f in db.fasi(lid)}
    if stati.get(nome) == "corso":
        raise ValueError("La fase è in corso")
    nuovo = "saltata" if nome == "voci" and not lav["voci_attive"] else "coda"
    db.aggiorna_fase(lid, nome, stato=nuovo, errore=None, progress=0, inizio=None, fine=None)
    for d in dipendenti(nome):
        if stati.get(d) in ("fatto", "errore"):
            db.aggiorna_fase(lid, d, stato="coda", errore=None, progress=0, inizio=None, fine=None)


# ── helper ───────────────────────────────────────────────────

def lingua_prodotti(lav: dict) -> str:
    if lav["lingua_prodotti"] and lav["lingua_prodotti"] != "auto":
        return lav["lingua_prodotti"]
    if lav.get("lingua_rilevata"):
        return lav["lingua_rilevata"]
    return lav["lingua"] if lav["lingua"] not in ("", "auto") else "it"


def termini(testo: str) -> list[str]:
    """Testo libero (virgole, punti e virgola, a capo) → termini unici, ordine conservato."""
    out, visti = [], set()
    for t in re.split(r"[\n,;]+", testo or ""):
        t = t.strip()
        if t and t.lower() not in visti:
            visti.add(t.lower())
            out.append(t)
    return out


def vocabolario(lav: dict) -> list[str]:
    """Vocabolario di riferimento del lavoro: quello del corso, altrimenti quello globale."""
    if lav.get("corso_id"):
        corso = db.riga("SELECT vocabolario FROM corsi WHERE id=?", lav["corso_id"])
        return termini(corso["vocabolario"]) if corso else []
    return termini(config.carica().get("vocabolario_globale", ""))


def initial_prompt(lav: dict) -> str | None:
    """Vocabolario globale + del corso + termini extra del lavoro → initial_prompt di whisper."""
    testo = config.carica().get("vocabolario_globale", "")
    if lav.get("corso_id"):
        corso = db.riga("SELECT vocabolario FROM corsi WHERE id=?", lav["corso_id"])
        if corso:
            testo += "\n" + corso["vocabolario"]
    termini_ = termini(testo + "\n" + (lav.get("termini_extra") or ""))
    if not termini_:
        return None
    out = ", ".join(termini_)
    return out[:800].rsplit(",", 1)[0] if len(out) > 800 else out


def etichettatore(lav: dict):
    """Etichetta voce → nome mostrato: nome scelto, parte (confronto) o «Voce N»."""
    if not lav["voci_attive"]:
        return lambda v: None
    vs = db.voci(lav["id"])
    nomi = {}
    for i, v in enumerate(vs):
        base = v["nome"] or f"Voce {i + 1}"
        if lav["profilo"] == "confronto" and v["parte"]:
            base = f"{v['nome']} ({v['parte']})" if v["nome"] else v["parte"]
        nomi[v["etichetta"]] = base
    return lambda v: nomi.get(v, "Voce ?") if v else "Voce ?"


def assegna_voci(segs: list[dict], turni: list[dict]) -> list[dict]:
    """Ogni segmento prende la voce con la massima sovrapposizione (o la più vicina)."""
    for s in segs:
        punteggi: dict[str, int] = {}
        for t in turni:
            ov = min(s["end_ms"], t["end_ms"]) - max(s["start_ms"], t["start_ms"])
            if ov > 0:
                punteggi[t["voce"]] = punteggi.get(t["voce"], 0) + ov
        if punteggi:
            s["voce"] = max(punteggi, key=punteggi.get)
        elif turni:
            centro = (s["start_ms"] + s["end_ms"]) // 2
            s["voce"] = min(turni, key=lambda t: min(abs(t["start_ms"] - centro), abs(t["end_ms"] - centro)))["voce"]
        else:
            s["voce"] = None
    return segs


def _note_testo(lid: str) -> str:
    note = db.json_campo(db.prodotto(lid, "note"), [])
    if not note:
        raise RuntimeError("Mancano le note di blocco: rigenera la fase «note»")
    return "\n\n---\n\n".join(note)


def _senza_recinto(t: str) -> str:
    t = t.strip()
    m = re.match(r"^```[a-z]*\n(.*)\n```$", t, re.S)
    return m.group(1).strip() if m else t


# ── esecuzione ───────────────────────────────────────────────

def esegui(lid: str, nome: str, motori, cfg: dict, progresso) -> None:
    lav = db.lavoro(lid)
    if lav is None:
        raise RuntimeError("Lavoro eliminato")
    cart = cartella(lid)

    if nome == "acquisizione":
        if lav["sorgente_tipo"] == "url":
            for vecchio in cart.glob("sorgente.*"):
                vecchio.unlink()
            meta = acquisizione.scarica_url(lav["sorgente"], cart)
            campi = {"file_sorgente": meta["file"], "meta_json": json.dumps(meta, ensure_ascii=False)}
            if meta["titolo"] and lav["titolo"] == lav["sorgente"]:
                campi["titolo"] = meta["titolo"]
            db.aggiorna_lavoro(lid, **campi)
        elif not (lav["file_sorgente"] and (cart / lav["file_sorgente"]).is_file()):
            raise RuntimeError("Il file caricato non si trova più nella cartella del lavoro")

    elif nome == "audio":
        lav = db.lavoro(lid)
        _, dur = acquisizione.prepara_audio(cart / lav["file_sorgente"], cart)
        db.aggiorna_lavoro(lid, durata_s=dur)

    elif nome == "trascrizione":
        with acquisizione.wav_temporaneo(cart / "audio.m4a") as wav:
            lingua, segs = motori.trascrittore.trascrivi(
                wav, None if lav["lingua"] in ("", "auto") else lav["lingua"], initial_prompt(lav), progresso)
        if not segs:
            raise RuntimeError("Nessun parlato riconosciuto nella registrazione")
        db.salva_segmenti(lid, segs)
        db.aggiorna_lavoro(lid, lingua_rilevata=lingua, trascritto_modificato=0)

    elif nome == "voci":
        with acquisizione.wav_temporaneo(cart / "audio.m4a") as wav:
            turni = motori.separatore.separa(wav)
        segs = assegna_voci(db.segmenti(lid), turni)
        db.salva_segmenti(lid, segs)
        vecchie = {v["etichetta"]: v for v in db.voci(lid)}
        with db.connetti() as c:
            c.execute("DELETE FROM voci WHERE lavoro_id=?", (lid,))
            for e in sorted({s["voce"] for s in segs if s["voce"]}):
                v = vecchie.get(e, {})
                c.execute("INSERT INTO voci(lavoro_id, etichetta, nome, parte) VALUES(?,?,?,?)",
                          (lid, e, v.get("nome", ""), v.get("parte", "")))

    elif nome == "note":
        lingua = lingua_prodotti(lav)
        parti = db.json_campo(lav["parti_json"], [])
        segs = [s for s in db.segmenti(lid) if not s["escluso"]]
        if not segs:
            raise RuntimeError("Tutto il trascritto è marcato come indesiderato: non resta nulla da riassumere")
        rs = mapreduce.righe(mapreduce.battute(segs, etichettatore(lav)))
        blocchi = mapreduce.spezza(rs)
        note = []
        progresso(0, f"0/{len(blocchi)}")
        for i, b in enumerate(blocchi, 1):
            note.append(motori.llm.genera(profili.prompt_note(lav["profilo"], b, lingua, parti)))
            progresso(i / (len(blocchi) + 1), f"{i}/{len(blocchi)}")
        note = mapreduce.condensa(note, lambda t: motori.llm.genera(profili.prompt_condensa(t, lingua)),
                                  mapreduce.budget_parole(int(cfg["llm_ctx"])))
        db.salva_prodotto(lid, "note", json.dumps(note, ensure_ascii=False))
        db.aggiorna_lavoro(lid, trascritto_modificato=0)

    elif nome == "prodotto":
        testo = motori.llm.genera(profili.prompt_prodotto(
            lav["profilo"], _note_testo(lid), lingua_prodotti(lav), db.json_campo(lav["parti_json"], [])))
        db.salva_prodotto(lid, "prodotto", _senza_recinto(testo))

    elif nome == "mappa":
        testo = motori.llm.genera(prompts_studio.prompt("mappa", _note_testo(lid), lingua_prodotti(lav)))
        db.salva_prodotto(lid, "mappa", _senza_recinto(testo))

    elif nome == "dispensa":
        lingua = lingua_prodotti(lav)
        if lav.get("dispensa_livello") == "approfondita":
            note = db.json_campo(db.prodotto(lid, "note"), [])
            if not note:
                raise RuntimeError("Mancano le note di blocco: rigenera la fase «note»")
            sezioni, titoli = [], []
            progresso(0, f"0/{len(note)}")
            for i, n in enumerate(note, 1):
                s = _senza_recinto(motori.llm.genera(prompts_studio.prompt_sezione(n, lingua, i, len(note), titoli)))
                sezioni.append(s)
                titoli += [r[3:].strip() for r in s.splitlines() if r.startswith("## ")]
                progresso(i / (len(note) + 1), f"{i}/{len(note)}")
            apertura = _senza_recinto(motori.llm.genera(prompts_studio.prompt_apertura("\n\n".join(sezioni), lingua)))
            testo = apertura + "\n\n" + "\n\n".join(sezioni)
        else:
            testo = _senza_recinto(motori.llm.genera(prompts_studio.prompt_dispensa(_note_testo(lid), lingua)))
        db.salva_prodotto(lid, "dispensa", prompts_studio.senza_tempi(testo))

    elif nome in prompts_studio.MODELLI:
        modello = prompts_studio.MODELLI[nome]
        p = prompts_studio.prompt(nome, _note_testo(lid), lingua_prodotti(lav))
        ultimo = ""
        for _ in range(2):  # un nuovo tentativo se il JSON non è valido
            try:
                ultimo = motori.llm.genera(p, prompts_studio.schema(nome))
                dati = modello.model_validate_json(_senza_recinto(ultimo))
                db.salva_prodotto(lid, nome, dati.model_dump_json())
                break
            except (ValidationError, ValueError):
                continue
        else:
            raise RuntimeError(f"Il modello non ha prodotto un {nome} valido dopo due tentativi")
    else:
        raise ValueError(f"Fase sconosciuta: {nome}")


def elimina_lavoro(lid: str) -> None:
    db.esegui("DELETE FROM lavori WHERE id=?", lid)
    shutil.rmtree(config.home() / "lavori" / lid, ignore_errors=True)
