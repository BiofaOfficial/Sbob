"""Export PDF (reportlab) da Markdown semplice."""
from __future__ import annotations

import contextlib
import re
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import markdown as md

_FONT_CANDIDATI = [
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
_FONT: str | None = None


def _font() -> str | None:
    """Font TrueType con frecce e simboli, se presente sul sistema."""
    global _FONT
    if _FONT is None:
        _FONT = ""
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        for f in _FONT_CANDIDATI:
            with contextlib.suppress(Exception):  # font assente o illeggibile: si prova il successivo
                pdfmetrics.registerFont(TTFont("SbobUni", f))
                _FONT = "SbobUni"
                break
    return _FONT or None


def _inline(t: str) -> str:
    if not _font():
        t = t.replace("→", "->").replace("—", "-").replace("◦", "-")
    t = escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)\*", r"<i>\1</i>", t)
    t = re.sub(r"_(.+?)_", r"<i>\1</i>", t)
    return t


def da_markdown(testo: str) -> bytes:
    st = getSampleStyleSheet()
    stili = {
        1: ParagraphStyle("h1", parent=st["Title"], fontSize=17, spaceAfter=6),
        2: ParagraphStyle("h2", parent=st["Heading2"]),
        3: ParagraphStyle("h3", parent=st["Heading3"]),
        4: ParagraphStyle("h4", parent=st["Heading4"]),
    }
    corpo = ParagraphStyle("b", parent=st["BodyText"], fontSize=10, leading=14)
    if _font():
        for x in [corpo, *stili.values()]:
            x.fontName = _font()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm)
    flow, tabella = [], []

    def chiudi_tabella():
        if tabella:
            t = Table([[Paragraph(_inline(c), corpo) for c in r] for r in tabella], colWidths=[50 * mm, 120 * mm])
            t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, "#999999"), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            flow.append(t)
            tabella.clear()

    for riga in testo.splitlines():
        s = riga.rstrip()
        if s.startswith("|"):
            celle = [c.strip() for c in s.strip("|").split("|")]
            if not all(re.fullmatch(r"-+", c) for c in celle):
                tabella.append(celle)
            continue
        chiudi_tabella()
        if not s.strip():
            flow.append(Spacer(1, 4))
            continue
        m = re.match(r"^(#{1,6})\s+(.*)", s)
        if m:
            flow.append(Paragraph(_inline(m.group(2)), stili[min(len(m.group(1)), 4)]))
            continue
        m = re.match(r"^(\s*)[-*]\s+(.*)", s)
        if m:
            liv = len(m.group(1)) // 2
            stile = ParagraphStyle(f"li{liv}", parent=corpo, leftIndent=12 + 12 * liv, bulletIndent=2 + 12 * liv)
            flow.append(Paragraph(_inline(m.group(2)), stile, bulletText="•" if liv == 0 or not _font() else "◦"))
            continue
        flow.append(Paragraph(_inline(s), corpo))
    chiudi_tabella()
    doc.build(flow)
    return buf.getvalue()


def documento(lav: dict, tipo: str) -> bytes:
    return da_markdown(md.documento(lav, tipo))
