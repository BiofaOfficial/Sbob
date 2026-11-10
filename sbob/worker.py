"""Coda dei lavori: una fase alla volta, riconciliazione, timeout, caffeinate."""
from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import shutil
import signal
import subprocess
import sys

from . import db
from .pipeline import fasi

log = logging.getLogger("sbob.worker")


class Caffeinate:
    """Il computer non va in stop durante un lavoro, e solo durante un lavoro.

    Mac: caffeinate. Linux: systemd-inhibit, se c'è; tiene il blocco finché vive Sbob o finché lo si ferma.
    """

    def __init__(self):
        self._p: subprocess.Popen | None = None

    def avvia(self):
        if self._p is not None:
            return
        pid = str(os.getpid())
        if sys.platform == "darwin":
            comando = ["caffeinate", "-i", "-w", pid]
        elif sys.platform.startswith("linux") and shutil.which("systemd-inhibit"):
            comando = ["systemd-inhibit", "--what=idle:sleep", "--who=Sbob", "--why=Lavoro in corso",
                       "tail", "--pid", pid, "-f", "/dev/null"]
        else:
            return
        try:
            self._p = subprocess.Popen(comando, start_new_session=True,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            self._p = None

    def ferma(self):
        if self._p is not None:
            try:
                os.killpg(self._p.pid, signal.SIGTERM)  # anche il processo figlio di systemd-inhibit
            except OSError:
                self._p.terminate()
            self._p = None


def riconcilia() -> None:
    """Le fasi interrotte da un riavvio tornano in coda."""
    db.esegui("UPDATE fasi SET stato='coda', progress=0 WHERE stato='corso'")


def prossima() -> tuple[str, str] | None:
    candidati = db.righe(
        "SELECT f.lavoro_id, f.nome FROM fasi f JOIN lavori l ON l.id=f.lavoro_id "
        "WHERE f.stato='coda' ORDER BY l.creato, f.ordine")
    cache: dict[str, dict] = {}
    for c in candidati:
        lid = c["lavoro_id"]
        if lid not in cache:
            cache[lid] = {f["nome"]: f["stato"] for f in db.fasi(lid)}
        if all(cache[lid].get(d) in ("fatto", "saltata") for d in fasi.ANTENATI[c["nome"]]):
            return lid, c["nome"]
    return None


class Worker:
    def __init__(self, motori, cfg: dict):
        self.motori = motori
        self.cfg = cfg
        self.evento = asyncio.Event()
        self.caff = Caffeinate()
        self._residente: str | None = None
        self.in_uso: str | None = None  # motore al lavoro in questo momento (stato UP)
        self._task: asyncio.Task | None = None

    def sveglia(self):
        self.evento.set()

    def _scarica(self, motore: str | None):
        if motore:
            try:
                getattr(self.motori, motore).scarica()
            except Exception as e:
                log.warning("Scarico %s non riuscito: %s", motore, e)

    async def esegui_una(self) -> bool:
        nxt = await asyncio.to_thread(prossima)
        if nxt is None:
            if self._residente:
                await asyncio.to_thread(self._scarica, self._residente)
                self._residente = None
            self.caff.ferma()
            return False
        lid, nome = nxt
        motore = fasi.MOTORE[nome]
        if self._residente and self._residente != motore:  # una cosa alla volta in memoria
            await asyncio.to_thread(self._scarica, self._residente)
        self._residente = motore
        self.caff.avvia()
        log.info("Lavoro %s: inizio fase %s", lid, nome)
        db.aggiorna_fase(lid, nome, stato="corso", inizio=db.adesso(), fine=None, errore=None, progress=0, dettaglio=None)
        self.in_uso = motore

        def progresso(x: float, dettaglio: str | None = None):
            campi = {"progress": round(min(max(x, 0.0), 1.0), 3)}
            if dettaglio is not None:
                campi["dettaglio"] = dettaglio
            db.aggiorna_fase(lid, nome, **campi)

        try:
            await asyncio.wait_for(
                asyncio.to_thread(fasi.esegui, lid, nome, self.motori, self.cfg, progresso),
                timeout=float(self.cfg["timeout_fase_s"]))
            db.aggiorna_fase(lid, nome, stato="fatto", fine=db.adesso(), progress=1)
        except TimeoutError:
            db.aggiorna_fase(lid, nome, stato="errore", fine=db.adesso(),
                             errore="Tempo massimo della fase superato")
        except Exception as e:  # nessun ritentativo automatico: si riprova dall'interfaccia
            log.exception("Fase %s del lavoro %s fallita", nome, lid)
            db.aggiorna_fase(lid, nome, stato="errore", fine=db.adesso(), errore=(str(e) or type(e).__name__)[:1000])
        finally:
            self.in_uso = None
        return True

    async def ciclo(self):
        while True:
            try:
                lavorato = await self.esegui_una()
            except Exception:
                log.exception("Errore del worker")
                lavorato = False
            if not lavorato:
                self.evento.clear()
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(self.evento.wait(), timeout=5)

    def avvia(self):
        riconcilia()
        self._task = asyncio.create_task(self.ciclo())

    async def ferma(self):
        if self._task:
            self._task.cancel()
        self.caff.ferma()
