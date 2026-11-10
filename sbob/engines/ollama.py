"""LLM locale via Ollama.

Streaming: il timeout misura il silenzio tra due token, non la durata totale.
A fine fase il modello si scarica dalla memoria (keep_alive: 0).
"""
from __future__ import annotations

import json
import logging
import time

import httpx

log = logging.getLogger("sbob.ollama")


class LLMOllama:
    def __init__(self, url: str, modello: str, ctx: int, transport: httpx.BaseTransport | None = None):
        self.url = url.rstrip("/")
        self.modello = modello
        self.ctx = ctx
        self._transport = transport

    def _client(self, timeout) -> httpx.Client:
        return httpx.Client(timeout=timeout, transport=self._transport)

    def genera(self, prompt: str, schema: dict | None = None) -> str:
        timeout = httpx.Timeout(connect=10.0, read=900.0, write=60.0, pool=10.0)
        corpo = {
            "model": self.modello, "prompt": prompt, "stream": True, "keep_alive": "15m",
            "options": {"temperature": 0.1, "num_ctx": self.ctx},
        }
        if schema:
            corpo["format"] = schema
        parti: list[str] = []
        t0 = time.monotonic()
        try:
            with self._client(timeout) as c, c.stream("POST", f"{self.url}/api/generate", json=corpo) as r:
                if r.status_code == 404:
                    raise RuntimeError(f"Modello '{self.modello}' non trovato in Ollama: scaricalo con «ollama pull {self.modello}»")
                r.raise_for_status()
                for riga in r.iter_lines():
                    if not riga.strip():
                        continue
                    ev = json.loads(riga)
                    if ev.get("error"):
                        raise RuntimeError(f"Ollama ha risposto con errore: {ev['error']}")
                    if ev.get("response"):
                        parti.append(ev["response"])
                    if ev.get("done"):
                        break
        except httpx.ConnectError as e:
            raise RuntimeError("Ollama non è raggiungibile: avvia l'app Ollama e riprova") from e
        except httpx.ReadTimeout as e:
            raise RuntimeError("Ollama non ha prodotto testo per oltre 15 minuti: modello troppo grande per questa macchina?") from e
        log.info("Ollama: %d pezzi in %.0fs", len(parti), time.monotonic() - t0)
        return "".join(parti).strip()

    def scarica(self) -> None:
        try:
            with self._client(httpx.Timeout(10.0)) as c:
                c.post(f"{self.url}/api/generate", json={"model": self.modello, "keep_alive": 0})
        except Exception as e:  # best effort
            log.warning("Scarico modello Ollama non riuscito: %s", e)

    def _ha(self, nomi: set) -> bool:
        return self.modello in nomi or f"{self.modello}:latest" in nomi

    def stato(self) -> dict:
        try:
            with self._client(httpx.Timeout(3.0)) as c:
                tags = c.get(f"{self.url}/api/tags").json()
                ps = c.get(f"{self.url}/api/ps").json()
            return {"raggiungibile": True,
                    "modello_presente": self._ha({m.get("name") for m in tags.get("models", [])}),
                    "caricato": self._ha({m.get("name") for m in ps.get("models", [])})}
        except Exception:
            return {"raggiungibile": False, "modello_presente": False, "caricato": False}

    def riscalda(self) -> None:
        """Carica il modello in memoria e ce lo tiene per 30 minuti."""
        try:
            with self._client(httpx.Timeout(connect=10.0, read=600.0, write=30.0, pool=10.0)) as c:
                r = c.post(f"{self.url}/api/generate", json={"model": self.modello, "prompt": "", "keep_alive": "30m"})
                r.raise_for_status()
        except httpx.ConnectError as e:
            raise RuntimeError("Ollama non è raggiungibile: avvia l'app Ollama e riprova") from e
