import json

from conftest import attendi, finito

from sbob import db
from sbob.worker import prossima, riconcilia


def crea(client, audio, **campi):
    with open(audio, "rb") as f:
        r = client.post("/api/lavori", data=campi, files={"file": ("lezione.mp3", f, "audio/mpeg")})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_lezione_completa_e_export(client, audio):
    lid = crea(client, audio)
    d = attendi(client, lid, finito)
    stati = {f["nome"]: f["stato"] for f in d["fasi"]}
    assert stati["voci"] == "saltata", stati
    assert all(stati[n] == "fatto" for n in ["trascrizione", "note", "prodotto", "mappa", "flashcard", "autoverifica", "glossario"]), d["fasi"]
    assert d["segmenti"] and d["prodotti"]["prodotto"]["contenuto"]
    assert all(f["inizio"] and f["fine"] for f in d["fasi"] if f["stato"] == "fatto")
    for tipo, fmt in [("prodotto", "md"), ("prodotto", "pdf"), ("mappa", "md"), ("flashcard", "txt"),
                      ("autoverifica", "pdf"), ("glossario", "md"), ("trascritto", "pdf")]:
        r = client.get(f"/api/lavori/{lid}/export/{tipo}.{fmt}")
        assert r.status_code == 200, (tipo, fmt, r.text)
        if fmt == "pdf":
            assert r.content[:4] == b"%PDF"
    assert "da rileggere" in client.get(f"/api/lavori/{lid}/export/prodotto.md").text
    r = client.get(f"/api/lavori/{lid}/audio", headers={"Range": "bytes=0-99"})
    assert r.status_code == 206 and len(r.content) == 100


def test_riunione_voci_rinomina_e_studio_a_richiesta(client, audio):
    lid = crea(client, audio, profilo="riunione")
    d = attendi(client, lid, finito)
    stati = {f["nome"]: f["stato"] for f in d["fasi"]}
    assert stati["voci"] == "fatto" and stati["flashcard"] == "manuale"
    assert [v["etichetta"] for v in d["voci"]] == ["SPEAKER_00", "SPEAKER_01"]
    assert d["segmenti"][0]["nome_voce"] == "Voce 1"
    trascr_prima = d["fasi"][2]["fine"]
    d = client.put(f"/api/lavori/{lid}/voci", json=[{"etichetta": "SPEAKER_00", "nome": "Marta"}]).json()
    d = attendi(client, lid, lambda d: finito(d) and d["prodotti"]["prodotto"])
    assert d["fasi"][2]["fine"] == trascr_prima  # la trascrizione non si rifà
    assert d["segmenti"][0]["nome_voce"] == "Marta"
    client.post(f"/api/lavori/{lid}/studio")
    d = attendi(client, lid, lambda d: all(f["stato"] == "fatto" for f in d["fasi"] if f["nome"] == "glossario"))
    assert "glossario" in d["prodotti"]


def test_confronto_con_parti(client, audio):
    lid = crea(client, audio, profilo="confronto", parti=json.dumps(["Docente", "Studente"]))
    attendi(client, lid, finito)
    client.put(f"/api/lavori/{lid}/voci", json=[{"etichetta": "SPEAKER_00", "parte": "Docente"},
                                                 {"etichetta": "SPEAKER_01", "parte": "Studente"}])
    d = attendi(client, lid, lambda d: finito(d) and d["segmenti"][0]["nome_voce"] == "Docente")
    assert d["parti"] == ["Docente", "Studente"]


def test_corsi_e_filtri(client, audio):
    c = client.post("/api/corsi", json={"nome": "Analisi 1", "vocabolario": "Cauchy"}).json()
    assert client.post("/api/corsi", json={"nome": "Analisi 1"}).status_code == 409
    lid = crea(client, audio, corso_id=str(c["id"]))
    crea(client, audio)
    assert [x["id"] for x in client.get(f"/api/lavori?corso={c['id']}").json()] == [lid]
    assert len(client.get("/api/lavori?corso=nessuno").json()) == 1
    client.patch(f"/api/lavori/{lid}", json={"senza_corso": True})
    assert client.get(f"/api/lavori/{lid}").json()["corso_id"] is None


def test_errori_leggibili_e_riprova(client, audio, monkeypatch):
    from sbob.engines import fake

    def rotto(self, *a, **k):
        raise RuntimeError("motore guasto")

    originale = fake.TrascrittoreFinto.trascrivi
    monkeypatch.setattr(fake.TrascrittoreFinto, "trascrivi", rotto)
    lid = crea(client, audio)
    d = attendi(client, lid, lambda d: any(f["stato"] == "errore" for f in d["fasi"]))
    f = next(f for f in d["fasi"] if f["stato"] == "errore")
    assert f["nome"] == "trascrizione" and f["errore"] == "motore guasto"
    monkeypatch.setattr(fake.TrascrittoreFinto, "trascrivi", originale)
    client.post(f"/api/lavori/{lid}/fasi/trascrizione/riprova")
    d = attendi(client, lid, lambda d: finito(d) and d["prodotti"].get("prodotto"))
    assert d["stato"] == "fatto", [(f["nome"], f["stato"], f["inizio"], f["fine"]) for f in d["fasi"]]


def test_json_non_valido_due_tentativi(client, audio, monkeypatch):
    from sbob.engines import fake
    originale = fake.LLMFinto.genera
    monkeypatch.setattr(fake.LLMFinto, "genera", lambda self, p, schema=None: "non json" if schema else originale(self, p))
    lid = crea(client, audio)
    d = attendi(client, lid, finito)
    f = {f["nome"]: f for f in d["fasi"]}
    assert f["flashcard"]["stato"] == "errore" and "due tentativi" in f["flashcard"]["errore"]


def test_riconciliazione_dopo_riavvio():
    db.migra()
    db.esegui("INSERT INTO lavori(id, titolo, profilo, sorgente_tipo, sorgente, creato) VALUES('x','t','lezione','file','f','1')")
    from sbob.pipeline import fasi
    fasi.crea_fasi("x", "lezione", False)
    db.aggiorna_fase("x", "acquisizione", stato="corso")
    riconcilia()
    assert prossima() == ("x", "acquisizione")


def test_validazioni_ingresso(client):
    assert client.post("/api/lavori", data={}).status_code == 400
    assert client.post("/api/lavori", data={"url": "ftp://x"}).status_code == 400
    assert client.post("/api/lavori", files={"file": ("a.exe", b"x")}).status_code == 400
    assert client.get("/api/profili").json()["default"] == "lezione"


def test_url_con_ytdlp_simulato(client, audio, monkeypatch):
    import shutil

    from sbob.pipeline import acquisizione

    def finto(url, cartella):
        shutil.copy(audio, cartella / "sorgente.m4a")
        return {"file": "sorgente.m4a", "titolo": "Video di prova", "data": "01/10/2026", "autore": "x", "url": url}

    monkeypatch.setattr(acquisizione, "scarica_url", finto)
    r = client.post("/api/lavori", data={"url": "https://www.youtube.com/watch?v=abc"})
    lid = r.json()["id"]
    d = attendi(client, lid, finito)
    assert d["titolo"] == "Video di prova" and d["meta"]["data"] == "01/10/2026"


def test_esclusioni_trascritto_e_rigenerazione(client, audio):
    lid = crea(client, audio)
    d = attendi(client, lid, finito)
    n = len(d["segmenti"])
    d = client.put(f"/api/lavori/{lid}/segmenti", json={"indici": [0, 1], "escluso": True}).json()
    assert d["trascritto_modificato"] == 1 and d["segmenti"][0]["escluso"] == 1
    client.post(f"/api/lavori/{lid}/fasi/note/riprova")
    d = attendi(client, lid, lambda d: finito(d) and d["trascritto_modificato"] == 0)
    note = next(f for f in d["fasi"] if f["nome"] == "note")
    assert note["dettaglio"] and note["dettaglio"].endswith("/1")
    client.put(f"/api/lavori/{lid}/segmenti", json={"indici": list(range(n)), "escluso": True})
    client.post(f"/api/lavori/{lid}/fasi/note/riprova")
    d = attendi(client, lid, lambda d: any(f["stato"] == "errore" for f in d["fasi"]))
    assert "indesiderato" in next(f for f in d["fasi"] if f["stato"] == "errore")["errore"]


def test_glossario_nel_vocabolario(client, audio):
    c = client.post("/api/corsi", json={"nome": "Fisica", "vocabolario": "Newton"}).json()
    lid = crea(client, audio, corso_id=str(c["id"]))
    r = client.post(f"/api/lavori/{lid}/vocabolario", json={"termini": ["newton", "Galileo"]}).json()
    assert r == {"vocabolario": ["Newton", "Galileo"], "dove": "corso"}
    lid2 = crea(client, audio)
    assert client.post(f"/api/lavori/{lid2}/vocabolario", json={"termini": ["Kepler"]}).json()["dove"] == "globale"
    assert client.get("/api/impostazioni").json()["vocabolario_globale"] == "Kepler"
    from sbob.pipeline import fasi
    assert fasi.initial_prompt({"corso_id": None, "termini_extra": "x"}) == "Kepler, x"


def test_stato_modelli_riscalda_export_completo(client, audio):
    s = client.get("/api/stato").json()
    assert s["modelli"]["llm"]["stato"] in ("WARM", "UP") and s["ctx"] == 16384 and s["hf_token"] is False
    assert client.post("/api/riscalda").status_code == 200
    lid = crea(client, audio)
    attendi(client, lid, finito)
    md = client.get(f"/api/lavori/{lid}/export/tutto.md").text
    assert "## Capitoli" in md and "## Glossario" in md and "## Trascritto" in md
    assert client.get(f"/api/lavori/{lid}/export/tutto.pdf").content[:4] == b"%PDF"


def test_esci(client):
    chiamato = []
    client.app.state.ferma = lambda: chiamato.append(True)
    assert client.post("/api/esci").json() == {"ok": True}
    import time
    time.sleep(0.8)
    assert chiamato == [True]


def test_voci_senza_token_bloccate_ovunque(client, audio):
    lid = crea(client, audio)
    attendi(client, lid, finito)
    motori = client.app.state.motori
    motori.nome = "mac"  # simula il Mac senza token: i motori restano finti
    try:
        assert client.get(f"/api/lavori/{lid}").json()["voci_disponibili"] is False
        r = client.patch(f"/api/lavori/{lid}", json={"voci_attive": True})
        assert r.status_code == 400 and "token Hugging Face" in r.json()["detail"]
        d = client.post(f"/api/lavori/{lid}/fasi/voci/riprova").json()  # lavoro senza voci: resta saltata
        assert next(f for f in d["fasi"] if f["nome"] == "voci")["stato"] == "saltata"
        with open(audio, "rb") as f:
            r = client.post("/api/lavori", data={"profilo": "riunione", "voci_attive": "1"}, files={"file": ("a.mp3", f)})
        assert r.status_code == 400
        with open(audio, "rb") as f:  # profilo con voci predefinite: senza token parte senza voci
            r = client.post("/api/lavori", data={"profilo": "riunione"}, files={"file": ("a.mp3", f)})
        assert r.status_code == 200 and r.json()["voci_attive"] == 0
    finally:
        motori.nome = "fake"


def test_cambio_lingua_rifa_la_trascrizione(client, audio):
    lid = crea(client, audio)
    d = attendi(client, lid, finito)
    client.patch(f"/api/lavori/{lid}", json={"lingua": "en"})
    # la nuova trascrizione rimette lingua_rilevata (azzerata dal cambio): segnale certo, a differenza
    # dell'orario di fine, che ha la risoluzione del secondo e con i motori finti può non cambiare
    d = attendi(client, lid, lambda d: finito(d) and d["lingua_rilevata"] == "en")
    assert d["lingua"] == "en" and d["lingua_rilevata"] == "en" and d["stato"] == "fatto"


def test_dispensa_su_richiesta(client, audio):
    lid = crea(client, audio)
    d = attendi(client, lid, finito)
    assert next(f for f in d["fasi"] if f["nome"] == "dispensa")["stato"] == "manuale"
    assert client.post(f"/api/lavori/{lid}/dispensa", json={"livello": "x"}).status_code == 400

    def fatta(d):
        return next(f for f in d["fasi"] if f["nome"] == "dispensa")["stato"] in ("fatto", "errore")

    for liv in ("sintetica", "approfondita"):
        assert client.post(f"/api/lavori/{lid}/dispensa", json={"livello": liv}).status_code == 200
        d = attendi(client, lid, fatta)
        assert d["dispensa_livello"] == liv
        testo = d["prodotti"]["dispensa"]["contenuto"]
        assert testo and "[00:" not in testo
    assert client.get(f"/api/lavori/{lid}/export/dispensa.pdf").content[:4] == b"%PDF"
