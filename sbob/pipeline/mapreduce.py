"""Map-reduce a blocchi.

Blocchi di ~1300 parole (≈10 minuti) senza tagliare le battute; reduce
gerarchica a budget, per non far troncare a Ollama i primi temi in silenzio.
"""
from __future__ import annotations

from collections.abc import Callable

PAROLE_BLOCCO = 1300
SECONDI_BATTUTA = 30


def mmss(ms: int) -> str:
    s = int(ms) // 1000
    h, m, s = s // 3600, (s // 60) % 60, s % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def battute(segs: list[dict], etichetta: Callable[[str | None], str | None]) -> list[dict]:
    """Fonde i segmenti consecutivi della stessa voce, a gruppi di ~30 s."""
    out: list[dict] = []
    for s in segs:
        voce = etichetta(s.get("voce"))
        if out and out[-1]["voce"] == voce and s["start_ms"] - out[-1]["start_ms"] < SECONDI_BATTUTA * 1000:
            out[-1]["testo"] += " " + s["testo"]
            out[-1]["end_ms"] = s["end_ms"]
        else:
            out.append({"voce": voce, "start_ms": s["start_ms"], "end_ms": s["end_ms"], "testo": s["testo"]})
    return out


def righe(bs: list[dict]) -> list[str]:
    return [(f"{b['voce']} [{mmss(b['start_ms'])}]: " if b["voce"] else f"[{mmss(b['start_ms'])}] ") + b["testo"]
            for b in bs]


def spezza(rs: list[str], max_parole: int = PAROLE_BLOCCO) -> list[str]:
    blocchi, corrente, n = [], [], 0
    for r in rs:
        k = len(r.split())
        if corrente and n + k > max_parole:
            blocchi.append("\n".join(corrente))
            corrente, n = [], 0
        corrente.append(r)
        n += k
    if corrente:
        blocchi.append("\n".join(corrente))
    return blocchi


def _gruppi(testi: list[str], budget: int) -> list[list[str]]:
    gruppi, corrente, n = [], [], 0
    for t in testi:
        k = len(t.split())
        if corrente and n + k > budget:
            gruppi.append(corrente)
            corrente, n = [], 0
        corrente.append(t)
        n += k
    if corrente:
        gruppi.append(corrente)
    return gruppi


def condensa(note: list[str], fondi: Callable[[str], str], budget: int) -> list[str]:
    """Riduce le note finché la loro somma sta nel budget di parole."""
    livello = note
    while len(livello) > 1 and sum(len(n.split()) for n in livello) > budget:
        gruppi = _gruppi(livello, budget)
        if len(gruppi) == len(livello):
            gruppi = [livello[i:i + 2] for i in range(0, len(livello), 2)]
        livello = [g[0] if len(g) == 1 else fondi("\n\n---\n\n".join(g)) for g in gruppi]
    return livello


def budget_parole(ctx_token: int) -> int:
    """Parole di input per un prompt di reduce: ~40% del contesto (1 parola ≈ 1,4 token)."""
    return max(800, int(ctx_token * 0.4 / 1.4))
