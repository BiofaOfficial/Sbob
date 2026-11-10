"""Motori intercambiabili: si scelgono all'avvio in base a piattaforma e config."""
from __future__ import annotations

from dataclasses import dataclass

from .base import LLM, SeparatoreVoci, Trascrittore


@dataclass
class Motori:
    nome: str
    trascrittore: Trascrittore
    separatore: SeparatoreVoci
    llm: LLM


def crea(cfg: dict, nome: str) -> Motori:
    if nome == "fake":
        from .fake import LLMFinto, SeparatoreFinto, TrascrittoreFinto
        return Motori("fake", TrascrittoreFinto(), SeparatoreFinto(), LLMFinto())
    if nome == "mac":
        from .mlx_whisper import TrascrittoreMLX
        from .ollama import LLMOllama
        from .pyannote import SeparatorePyannote
        return Motori(
            "mac",
            TrascrittoreMLX(cfg["whisper_modello"]),
            SeparatorePyannote(lambda: cfg.get("hf_token", "")),
            LLMOllama(cfg["ollama_url"], cfg["llm_modello"], int(cfg["llm_ctx"])),
        )
    if nome == "linux":
        from .faster_whisper import TrascrittoreFW
        from .ollama import LLMOllama
        from .pyannote import SeparatorePyannote
        return Motori(
            "linux",
            TrascrittoreFW(cfg["whisper_modello"]),
            SeparatorePyannote(lambda: cfg.get("hf_token", "")),
            LLMOllama(cfg["ollama_url"], cfg["llm_modello"], int(cfg["llm_ctx"])),
        )
    raise ValueError(f"Motori sconosciuti: {nome}")
