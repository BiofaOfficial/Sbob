"""Flashcard → file di testo importabile in Anki (separatore tabulazione)."""
from __future__ import annotations

import html
import json

from .. import db


def _pulisci(s: str) -> str:
    return html.escape(s.strip()).replace("\t", " ").replace("\n", "<br>")


def tsv(lid: str) -> str:
    d = json.loads(db.prodotto(lid, "flashcard"))
    righe = ["#separator:tab", "#html:true", "#tags column:3"]
    righe += [f"{_pulisci(c['domanda'])}\t{_pulisci(c['risposta'])}\tsbob" for c in d["carte"]]
    return "\n".join(righe) + "\n"
