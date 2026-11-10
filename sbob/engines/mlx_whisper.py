"""Trascrizione su GPU Apple con mlx-whisper (motore Mac della v1)."""
from __future__ import annotations

import contextlib
import gc
import logging

log = logging.getLogger("sbob.whisper")


class TrascrittoreMLX:
    def __init__(self, modello: str):
        self.modello = modello

    def trascrivi(self, wav, lingua, initial_prompt, progresso=None):
        import mlx_whisper  # import pigro: solo su Mac

        r = mlx_whisper.transcribe(
            wav,
            path_or_hf_repo=self.modello,
            language=None if lingua in (None, "", "auto") else lingua,
            initial_prompt=initial_prompt or None,
            condition_on_previous_text=False,  # riduce le ripetizioni in loop sulle lezioni lunghe
            verbose=None,
        )
        segs = [
            {"start_ms": int(s["start"] * 1000), "end_ms": int(s["end"] * 1000), "testo": s["text"].strip()}
            for s in r.get("segments", []) if s.get("text", "").strip()
        ]
        if progresso:
            progresso(1.0)
        return r.get("language") or (lingua or "it"), segs

    def scarica(self):
        # best effort: le API interne di mlx cambiano tra versioni, lo scarico non deve mai far fallire una fase
        with contextlib.suppress(Exception):
            from mlx_whisper.transcribe import ModelHolder
            ModelHolder.model = None
            ModelHolder.model_path = None
        gc.collect()
        with contextlib.suppress(Exception):
            import mlx.core as mx
            (getattr(mx, "clear_cache", None) or mx.metal.clear_cache)()
        log.info("Modello whisper scaricato dalla memoria")

    def stato(self) -> dict:
        try:
            import mlx_whisper  # noqa: F401
            from mlx_whisper.transcribe import ModelHolder
        except Exception:
            return {"installato": False, "scaricato": False, "caricato": False}
        try:
            from huggingface_hub import try_to_load_from_cache
            scaricato = isinstance(try_to_load_from_cache(self.modello, "config.json"), str)
        except Exception:
            scaricato = False
        return {"installato": True, "scaricato": scaricato,
                "caricato": ModelHolder.model is not None and ModelHolder.model_path == self.modello}

    def riscalda(self) -> None:
        import mlx.core as mx
        from mlx_whisper.transcribe import ModelHolder
        ModelHolder.get_model(self.modello, mx.float16)
