"""Trascrizione su Linux con faster-whisper: scheda NVIDIA se c'è, altrimenti CPU."""
from __future__ import annotations

import gc
import logging
import os

log = logging.getLogger("sbob.whisper")


class TrascrittoreFW:
    def __init__(self, modello: str):
        self.modello = modello
        self._m = None
        self._caricato: str | None = None  # nome del modello in memoria
        self.dispositivo: str | None = None  # cuda | cpu, noto dopo il primo caricamento

    @staticmethod
    def _preferito() -> tuple[str, str]:
        try:
            import ctranslate2
            if ctranslate2.get_cuda_device_count() > 0:
                return "cuda", "float16"
        except Exception as e:
            log.warning("Scheda NVIDIA non rilevabile (%s): uso la CPU", e)
        return "cpu", "int8"

    def _carica(self, forza_cpu: bool = False):
        if self._m is not None and self._caricato == self.modello and not forza_cpu:
            return self._m
        from faster_whisper import WhisperModel  # import pigro: solo su Linux

        self.scarica()
        device, tipo = ("cpu", "int8") if forza_cpu else self._preferito()
        try:
            m = WhisperModel(self.modello, device=device, compute_type=tipo)
        except Exception as e:
            if device == "cpu":
                raise
            log.warning("Scheda NVIDIA non utilizzabile (%s): uso la CPU", e)
            device, tipo = "cpu", "int8"
            m = WhisperModel(self.modello, device=device, compute_type=tipo)
        self._m, self._caricato, self.dispositivo = m, self.modello, device
        log.info("Modello whisper %s caricato su %s", self.modello, device)
        return m

    def _segmenti(self, m, wav, lingua, initial_prompt, progresso):
        segmenti, info = m.transcribe(
            wav,
            language=None if lingua in (None, "", "auto") else lingua,
            initial_prompt=initial_prompt or None,
            condition_on_previous_text=False,  # riduce le ripetizioni in loop sulle lezioni lunghe
            vad_filter=True,  # salta i silenzi: meno testo inventato
        )
        out = []
        durata = float(getattr(info, "duration", 0) or 0)
        for s in segmenti:  # generatore: la trascrizione avviene qui, un pezzo alla volta
            testo = s.text.strip()
            if testo:
                out.append({"start_ms": int(s.start * 1000), "end_ms": int(s.end * 1000), "testo": testo})
            if progresso and durata:
                progresso(min(s.end / durata, 0.99))
        return info.language, out

    def trascrivi(self, wav, lingua, initial_prompt, progresso=None):
        try:
            rilevata, segs = self._segmenti(self._carica(), wav, lingua, initial_prompt, progresso)
        except RuntimeError as e:  # tipico: librerie CUDA/cuDNN mancanti o memoria video esaurita
            if self.dispositivo != "cuda":
                raise
            log.warning("Trascrizione sulla scheda NVIDIA fallita (%s): ripeto sulla CPU", e)
            rilevata, segs = self._segmenti(self._carica(forza_cpu=True), wav, lingua, initial_prompt, progresso)
        if progresso:
            progresso(1.0)
        return rilevata or (lingua or "it"), segs

    def scarica(self):
        if self._m is not None:
            self._m, self._caricato = None, None
            gc.collect()
            log.info("Modello whisper scaricato dalla memoria")

    def _in_cache(self) -> bool:
        if os.path.isdir(self.modello):
            return True
        try:
            from faster_whisper.utils import _MODELS
            from huggingface_hub import try_to_load_from_cache
            repo = _MODELS.get(self.modello, self.modello)
            return "/" in repo and isinstance(try_to_load_from_cache(repo, "model.bin"), str)
        except Exception:
            return False

    def stato(self) -> dict:
        try:
            import faster_whisper  # noqa: F401
        except Exception:
            return {"installato": False, "scaricato": False, "caricato": False}
        return {"installato": True, "scaricato": self._in_cache(),
                "caricato": self._m is not None and self._caricato == self.modello}

    def riscalda(self) -> None:
        self._carica()
