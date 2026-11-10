"""Separazione delle voci con pyannote su GPU (MPS su Mac, CUDA su Linux) con ripiego sulla CPU."""
from __future__ import annotations

import contextlib
import gc
import logging
import wave
from collections.abc import Callable

log = logging.getLogger("sbob.voci")
MODELLO = "pyannote/speaker-diarization-3.1"


class SeparatorePyannote:
    def __init__(self, token: Callable[[], str]):
        self._token = token
        self._pipe = None

    def _carica(self):
        if self._pipe is not None:
            return self._pipe
        tok = self._token()
        if not tok:
            raise RuntimeError("Separazione voci non configurata: manca il token Hugging Face (Impostazioni)")
        import torch
        from pyannote.audio import Pipeline
        try:
            pipe = Pipeline.from_pretrained(MODELLO, token=tok)
        except TypeError:  # pyannote 3.x
            pipe = Pipeline.from_pretrained(MODELLO, use_auth_token=tok)
        if pipe is None:
            raise RuntimeError("Accesso al modello pyannote non concesso: accetta la licenza su Hugging Face")
        gpu = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else None
        if gpu:
            try:
                pipe.to(torch.device(gpu))
            except Exception as e:
                log.warning("GPU (%s) non utilizzabile, uso la CPU: %s", gpu, e)
        self._pipe = pipe
        return pipe

    def separa(self, wav):
        import numpy as np
        import torch

        pipe = self._carica()
        with wave.open(wav, "rb") as w:
            sr = w.getframerate()
            raw = w.readframes(w.getnframes())
        dati = torch.from_numpy(np.frombuffer(raw, dtype=np.int16).astype("float32") / 32768.0).unsqueeze(0)
        try:
            out = pipe({"waveform": dati, "sample_rate": sr})
        except Exception as e:  # operazioni non supportate o memoria video esaurita → CPU
            log.warning("Separazione sulla GPU fallita (%s), ripeto sulla CPU", e)
            pipe.to(torch.device("cpu"))
            out = pipe({"waveform": dati, "sample_rate": sr})
        ann = getattr(out, "speaker_diarization", out)
        turni = [{"start_ms": int(t.start * 1000), "end_ms": int(t.end * 1000), "voce": spk}
                 for t, _, spk in ann.itertracks(yield_label=True)]
        return sorted(turni, key=lambda t: t["start_ms"])

    def scarica(self):
        self._pipe = None
        gc.collect()
        with contextlib.suppress(Exception):  # best effort
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            elif torch.backends.mps.is_available():
                torch.mps.empty_cache()

    def stato(self) -> dict:
        try:
            import pyannote.audio  # noqa: F401
            inst = True
        except Exception:
            inst = False
        return {"installato": inst, "token": bool(self._token())}
