"""Interfacce comuni dei tre motori pesanti."""
from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

Progresso = Callable[[float], None]


class Trascrittore(Protocol):
    def trascrivi(self, wav: str, lingua: str | None, initial_prompt: str | None,
                  progresso: Progresso | None = None) -> tuple[str, list[dict]]:
        """→ (lingua rilevata, [{start_ms, end_ms, testo}])"""

    def scarica(self) -> None: ...


class SeparatoreVoci(Protocol):
    def separa(self, wav: str) -> list[dict]:
        """→ [{start_ms, end_ms, voce}] ordinati per inizio"""

    def scarica(self) -> None: ...


class LLM(Protocol):
    def genera(self, prompt: str, schema: dict | None = None) -> str: ...

    def scarica(self) -> None: ...
