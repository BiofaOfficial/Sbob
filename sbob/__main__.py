"""Avvio di Sbob: server locale e apertura del browser.

  python -m sbob            avvia e apre il browser
  python -m sbob --no-browser
  python -m sbob check      verifica i motori veri (whisper, Ollama, voci)
"""
from __future__ import annotations

import argparse
import logging
import socket
import sys
import threading
import webbrowser


def _occupata(porta: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", porta)) == 0


def check() -> int:
    import math
    import os
    import struct
    import tempfile
    import time
    import wave

    from . import config, engines

    cfg = config.carica()
    nome = config.motori_effettivi(cfg)
    print(f"Motori: {nome}   cartella dati: {config.home()}")
    m = engines.crea(cfg, nome)
    ok = True
    fd, wav = tempfile.mkstemp(suffix=".wav", prefix="sbob_check_")
    os.close(fd)
    with wave.open(wav, "wb") as w:  # 3 s di tono: basta a far girare il modello
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"".join(struct.pack("<h", int(3000 * math.sin(i / 8))) for i in range(48000)))
    for etichetta, fn in [
        ("Trascrizione", lambda: m.trascrittore.trascrivi(wav, "it", None)),
        ("LLM", lambda: m.llm.genera("Rispondi solo: ok")),
        ("Separazione voci", lambda: m.separatore.separa(wav) if cfg.get("hf_token") or nome == "fake" else "saltata (nessun token HF)"),
    ]:
        t0 = time.monotonic()
        try:
            r = fn()
            print(f"  OK  {etichetta} ({time.monotonic() - t0:.1f}s): {str(r)[:80]}")
        except Exception as e:
            ok = False
            print(f"  KO  {etichetta}: {e}")
        for k in ("trascrittore", "llm", "separatore"):
            getattr(m, k).scarica()
    os.remove(wav)
    return 0 if ok else 1


def main() -> None:
    ap = argparse.ArgumentParser(prog="sbob")
    ap.add_argument("comando", nargs="?", default="avvia", choices=["avvia", "check"])
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--porta", type=int)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    if a.comando == "check":
        sys.exit(check())

    from . import config
    cfg = config.carica()
    porta = a.porta or int(cfg["porta"])
    indirizzo = f"http://127.0.0.1:{porta}"
    if _occupata(porta):  # già avviato: apre solo il browser
        print(f"Sbob è già in esecuzione: {indirizzo}")
        if not a.no_browser:
            webbrowser.open(indirizzo)
        return
    import uvicorn

    from .api import crea_app
    app = crea_app(cfg)
    if not a.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(indirizzo)).start()
    print(f"Sbob in esecuzione su {indirizzo} — chiudi questa finestra per fermarlo")
    uvicorn.run(app, host="127.0.0.1", port=porta, log_level="warning")


if __name__ == "__main__":
    main()
