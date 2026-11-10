"""Storico in SQLite: schema, migrazioni (PRAGMA user_version) e accesso.

Una connessione per operazione: semplice e sicuro tra il worker e le richieste.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from . import config

MIGRAZIONI = [
    """
    CREATE TABLE corsi(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        vocabolario TEXT NOT NULL DEFAULT '',
        creato TEXT NOT NULL
    );
    CREATE TABLE lavori(
        id TEXT PRIMARY KEY,
        titolo TEXT NOT NULL,
        corso_id INTEGER REFERENCES corsi(id) ON DELETE SET NULL,
        profilo TEXT NOT NULL,
        sorgente_tipo TEXT NOT NULL,      -- file | url
        sorgente TEXT NOT NULL,           -- nome file originale o URL
        file_sorgente TEXT,               -- nome del file nella cartella del lavoro
        lingua TEXT NOT NULL DEFAULT 'auto',
        lingua_rilevata TEXT,
        lingua_prodotti TEXT NOT NULL DEFAULT 'auto',
        voci_attive INTEGER NOT NULL DEFAULT 0,
        termini_extra TEXT NOT NULL DEFAULT '',
        parti_json TEXT NOT NULL DEFAULT '[]',
        durata_s REAL,
        meta_json TEXT NOT NULL DEFAULT '{}',
        creato TEXT NOT NULL
    );
    CREATE TABLE fasi(
        lavoro_id TEXT NOT NULL REFERENCES lavori(id) ON DELETE CASCADE,
        nome TEXT NOT NULL,
        ordine INTEGER NOT NULL,
        stato TEXT NOT NULL,              -- coda | corso | fatto | errore | saltata | manuale
        inizio TEXT, fine TEXT, errore TEXT,
        progress REAL NOT NULL DEFAULT 0,
        PRIMARY KEY(lavoro_id, nome)
    );
    CREATE TABLE segmenti(
        lavoro_id TEXT NOT NULL REFERENCES lavori(id) ON DELETE CASCADE,
        indice INTEGER NOT NULL,
        start_ms INTEGER NOT NULL, end_ms INTEGER NOT NULL,
        testo TEXT NOT NULL,
        voce TEXT,
        PRIMARY KEY(lavoro_id, indice)
    );
    CREATE TABLE voci(
        lavoro_id TEXT NOT NULL REFERENCES lavori(id) ON DELETE CASCADE,
        etichetta TEXT NOT NULL,
        nome TEXT NOT NULL DEFAULT '',
        parte TEXT NOT NULL DEFAULT '',
        PRIMARY KEY(lavoro_id, etichetta)
    );
    CREATE TABLE prodotti(
        lavoro_id TEXT NOT NULL REFERENCES lavori(id) ON DELETE CASCADE,
        tipo TEXT NOT NULL,
        contenuto TEXT NOT NULL,
        aggiornato TEXT NOT NULL,
        PRIMARY KEY(lavoro_id, tipo)
    );
    """,
    """
    ALTER TABLE segmenti ADD COLUMN escluso INTEGER NOT NULL DEFAULT 0;
    ALTER TABLE fasi ADD COLUMN dettaglio TEXT;
    ALTER TABLE lavori ADD COLUMN trascritto_modificato INTEGER NOT NULL DEFAULT 0;
    """,
    """
    ALTER TABLE lavori ADD COLUMN dispensa_livello TEXT NOT NULL DEFAULT 'sintetica';
    INSERT OR IGNORE INTO fasi(lavoro_id, nome, ordine, stato) SELECT id, 'dispensa', 10, 'manuale' FROM lavori;
    """,
]


def adesso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def percorso_db() -> Path:
    return config.home() / "sbob.db"


@contextmanager
def connetti():
    conn = sqlite3.connect(percorso_db(), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def migra() -> None:
    with connetti() as c:
        c.execute("PRAGMA journal_mode=WAL")
        v = c.execute("PRAGMA user_version").fetchone()[0]
        for i, sql in enumerate(MIGRAZIONI[v:], start=v + 1):
            c.executescript(sql)
            c.execute(f"PRAGMA user_version={i}")


def righe(sql: str, *args) -> list[dict]:
    with connetti() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]


def riga(sql: str, *args) -> dict | None:
    r = righe(sql, *args)
    return r[0] if r else None


def esegui(sql: str, *args) -> int:
    with connetti() as c:
        cur = c.execute(sql, args)
        return cur.lastrowid


# ── helper di dominio ────────────────────────────────────────

def lavoro(lid: str) -> dict | None:
    return riga("SELECT * FROM lavori WHERE id=?", lid)


def aggiorna_lavoro(lid: str, **campi) -> None:
    if not campi:
        return
    sets = ", ".join(f"{k}=?" for k in campi)
    # i nomi delle colonne arrivano dal codice (kwargs), mai dall'utente
    esegui(f"UPDATE lavori SET {sets} WHERE id=?", *campi.values(), lid)  # noqa: S608


def fasi(lid: str) -> list[dict]:
    return righe("SELECT * FROM fasi WHERE lavoro_id=? ORDER BY ordine", lid)


def aggiorna_fase(lid: str, nome: str, **campi) -> None:
    sets = ", ".join(f"{k}=?" for k in campi)
    esegui(f"UPDATE fasi SET {sets} WHERE lavoro_id=? AND nome=?", *campi.values(), lid, nome)  # noqa: S608


def prodotto(lid: str, tipo: str) -> str | None:
    r = riga("SELECT contenuto FROM prodotti WHERE lavoro_id=? AND tipo=?", lid, tipo)
    return r["contenuto"] if r else None


def salva_prodotto(lid: str, tipo: str, contenuto: str) -> None:
    esegui(
        "INSERT INTO prodotti(lavoro_id, tipo, contenuto, aggiornato) VALUES(?,?,?,?) "
        "ON CONFLICT(lavoro_id, tipo) DO UPDATE SET contenuto=excluded.contenuto, aggiornato=excluded.aggiornato",
        lid, tipo, contenuto, adesso(),
    )


def segmenti(lid: str) -> list[dict]:
    return righe("SELECT * FROM segmenti WHERE lavoro_id=? ORDER BY indice", lid)


def salva_segmenti(lid: str, segs: list[dict]) -> None:
    with connetti() as c:
        c.execute("DELETE FROM segmenti WHERE lavoro_id=?", (lid,))
        c.executemany(
            "INSERT INTO segmenti(lavoro_id, indice, start_ms, end_ms, testo, voce, escluso) VALUES(?,?,?,?,?,?,?)",
            [(lid, i, s["start_ms"], s["end_ms"], s["testo"], s.get("voce"), int(s.get("escluso") or 0))
             for i, s in enumerate(segs)],
        )


def voci(lid: str) -> list[dict]:
    return righe("SELECT * FROM voci WHERE lavoro_id=? ORDER BY etichetta", lid)


def json_campo(valore: str | None, default):
    try:
        return json.loads(valore) if valore else default
    except ValueError:
        return default
