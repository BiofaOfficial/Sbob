"""Motori finti e deterministici: test e sviluppo fuori da macOS."""
from __future__ import annotations

import json
import os
import time
import wave


def _attesa():
    """SBOB_FAKE_RITARDO=secondi rallenta i motori finti (per vedere l'avanzamento)."""
    time.sleep(float(os.environ.get("SBOB_FAKE_RITARDO") or 0))


def _durata_wav(wav: str) -> float:
    try:
        with wave.open(wav, "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return 60.0


class TrascrittoreFinto:
    def trascrivi(self, wav, lingua, initial_prompt, progresso=None):
        _attesa()
        dur = max(_durata_wav(wav), 1.0)
        n = max(3, min(40, int(dur // 10)))
        passo = int(dur * 1000 / n)
        segs = [
            {"start_ms": i * passo, "end_ms": (i + 1) * passo,
             "testo": f"Frase di prova numero {i + 1} sul concetto {chr(65 + i % 26)}."}
            for i in range(n)
        ]
        if progresso:
            progresso(1.0)
        return (lingua or "it"), segs

    def scarica(self):
        pass


class SeparatoreFinto:
    def separa(self, wav):
        dur_ms = int(max(_durata_wav(wav), 1.0) * 1000)
        meta = dur_ms // 2
        return [
            {"start_ms": 0, "end_ms": meta, "voce": "SPEAKER_00"},
            {"start_ms": meta, "end_ms": dur_ms, "voce": "SPEAKER_01"},
        ]

    def scarica(self):
        pass


class LLMFinto:
    """Restituisce JSON valido per lo schema richiesto, altrimenti Markdown."""

    def __init__(self):
        self.chiamate: list[str] = []

    def genera(self, prompt, schema=None):
        _attesa()
        self.chiamate.append(prompt)
        if schema:
            props = schema.get("properties", {})
            chiave = next(iter(props))
            voce = props[chiave]["items"]
            ref = voce.get("$ref", "").split("/")[-1]
            campi = list((schema.get("$defs", {}).get(ref) or voce).get("properties", {}))
            return json.dumps({chiave: [{c: f"{c} {i + 1}" for c in campi} for i in range(5)]})
        return ("# Lezione di prova\n\n### IN BREVE\nRiassunto di prova.\n\n"
                "### CAPITOLI\n- [00:00] Introduzione — contenuto.\n- [00:30] Sviluppo — contenuto.\n\n"
                "## Ramo\n- foglia [00:10]\n")

    def scarica(self):
        pass
