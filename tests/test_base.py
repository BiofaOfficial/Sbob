import json

from sbob import config, db, profili, prompts_studio
from sbob.engines.fake import LLMFinto
from sbob.engines.ollama import LLMOllama
from sbob.pipeline import fasi, mapreduce


def test_config_default_e_salvataggio(home):
    cfg = config.carica()
    assert cfg["porta"] == 8765 and cfg["hf_token"] == ""
    cfg["hf_token"] = "segreto"
    config.salva(cfg)
    assert config.carica()["hf_token"] == "segreto"
    assert (home / "config.toml").stat().st_mode & 0o077 == 0


def test_migrazione_idempotente():
    db.migra()
    db.migra()
    assert db.riga("PRAGMA user_version")["user_version"] == len(db.MIGRAZIONI)


def test_mmss_e_blocchi():
    assert mapreduce.mmss(65_000) == "01:05" and mapreduce.mmss(3_725_000) == "1:02:05"
    segs = [{"start_ms": i * 5000, "end_ms": i * 5000 + 5000, "testo": "parola " * 100, "voce": None} for i in range(40)]
    bs = mapreduce.battute(segs, lambda v: None)
    assert all(b["end_ms"] - b["start_ms"] <= 35_000 for b in bs)
    blocchi = mapreduce.spezza(mapreduce.righe(bs))
    assert len(blocchi) >= 3 and all(len(b.split()) <= 1400 for b in blocchi)


def test_condensa_rispetta_budget():
    llm = LLMFinto()
    note = ["parola " * 500 for _ in range(8)]
    out = mapreduce.condensa(note, lambda t: llm.genera(t), 1200)
    assert sum(len(n.split()) for n in out) <= 1200 or len(out) == 1
    assert llm.chiamate


def test_prompt_con_graffe_e_lingue():
    p = profili.prompt_note("lezione", "f(x) = {a, b}", "it")
    assert "{a, b}" in p and "Rispondi in italiano" in p
    assert "Write your answer in English" in profili.prompt_prodotto("riunione", "x", "en")
    assert "Docente" in profili.prompt_prodotto("confronto", "x", "it", ["Docente", "Studente"])
    assert "español" in prompts_studio.prompt("glossario", "x", "es")


def test_assegna_voci():
    segs = [{"start_ms": 0, "end_ms": 1000}, {"start_ms": 1500, "end_ms": 3000}, {"start_ms": 9000, "end_ms": 9500}]
    turni = [{"start_ms": 0, "end_ms": 1200, "voce": "A"}, {"start_ms": 1200, "end_ms": 4000, "voce": "B"}]
    assert [s["voce"] for s in fasi.assegna_voci(segs, turni)] == ["A", "B", "B"]


def test_initial_prompt_da_corso():
    db.migra()
    cid = db.esegui("INSERT INTO corsi(nome, vocabolario, creato) VALUES('Analisi 1', 'Weierstrass, Cauchy\nlimite', 'x')")
    lav = {"corso_id": cid, "termini_extra": "cauchy; Bolzano"}
    assert fasi.initial_prompt(lav) == "Weierstrass, Cauchy, limite, Bolzano"
    assert fasi.initial_prompt({"corso_id": None, "termini_extra": ""}) is None


def test_ollama_streaming_e_schema():
    import httpx

    visti = {}

    def gestore(req):
        visti.update(json.loads(req.content))
        righe = [json.dumps({"response": "ci"}), json.dumps({"response": "ao", "done": True})]
        return httpx.Response(200, text="\n".join(righe))

    llm = LLMOllama("http://x", "m", 4096, transport=httpx.MockTransport(gestore))
    assert llm.genera("p", {"type": "object"}) == "ciao"
    assert visti["format"] == {"type": "object"} and visti["options"]["num_ctx"] == 4096


def test_ollama_errore_leggibile():
    import httpx
    import pytest

    def gestore(req):
        raise httpx.ConnectError("no")

    llm = LLMOllama("http://x", "m", 4096, transport=httpx.MockTransport(gestore))
    with pytest.raises(RuntimeError, match="Ollama non è raggiungibile"):
        llm.genera("p")
