"""Sbob non ha login: le richieste non locali vanno rifiutate (DNS rebinding, CSRF)."""
import pytest
from fastapi.testclient import TestClient

from sbob.api import _locale, crea_app


@pytest.mark.parametrize("valore, atteso", [
    ("127.0.0.1:8765", True), ("localhost", True), ("[::1]:8765", True),
    ("http://localhost:5173", True), ("http://127.0.0.1:8765", True),
    ("evil.example", False), ("http://evil.example", False), ("127.0.0.1.evil.example", False),
    ("null", False), ("", False),
])
def test_locale(valore, atteso):
    assert _locale(valore) is atteso


def test_host_estraneo_rifiutato():
    with TestClient(crea_app(), base_url="http://evil.example") as c:
        assert c.get("/api/stato").status_code == 403


def test_origin_estranea_rifiutata(client):
    assert client.post("/api/corsi", json={"nome": "X"}, headers={"Origin": "http://evil.example"}).status_code == 403
    assert client.post("/api/corsi", json={"nome": "X"}, headers={"Origin": "null"}).status_code == 403
    assert client.get("/api/corsi").json() == []
    assert client.post("/api/corsi", json={"nome": "X"}, headers={"Origin": "http://localhost:5173"}).status_code == 200


def test_esci_non_raggiungibile_da_altre_pagine(client):
    chiamate = []
    client.app.state.ferma = lambda: chiamate.append(1)
    assert client.post("/api/esci", headers={"Origin": "http://evil.example"}).status_code == 403
    assert chiamate == []


def test_corso_modifica_validata(client):
    a = client.post("/api/corsi", json={"nome": "Analisi"}).json()
    client.post("/api/corsi", json={"nome": "Fisica"})
    assert client.put("/api/corsi/999", json={"nome": "Boh"}).status_code == 404
    assert client.put(f"/api/corsi/{a['id']}", json={"nome": " "}).status_code == 400
    assert client.put(f"/api/corsi/{a['id']}", json={"nome": "Fisica"}).status_code == 409
    assert client.put(f"/api/corsi/{a['id']}", json={"nome": "Analisi 1"}).json()["nome"] == "Analisi 1"
    assert client.get("/api/lavori?corso=abc").status_code == 400
