"""Acquisizione della sorgente e preparazione dell'audio (ffmpeg, yt-dlp).

Scaricamento da URL: metadati prima, poi il solo audio in m4a; errori di
yt-dlp resi leggibili.
"""
from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

ESTENSIONI = {".mp4", ".mkv", ".mov", ".avi", ".m4v", ".webm", ".mp3", ".wav", ".m4a",
              ".aac", ".ogg", ".opus", ".flac", ".wma", ".amr", ".3gp", ".caf"}
TIMEOUT_METADATI_S = 90
TIMEOUT_DOWNLOAD_S = 3600


def _ytdlp(argomenti: list[str], timeout: float) -> str:
    try:
        p = subprocess.run(
            [sys.executable, "-m", "yt_dlp", "--ignore-config", "--no-playlist", "--no-progress",
             "--no-warnings", *argomenti],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Lo scaricamento non ha risposto entro {int(timeout)} s: operazione interrotta") from None
    if p.returncode != 0:
        dettaglio = "\n".join(p.stderr.strip().splitlines()[-3:])
        raise RuntimeError(f"Scaricamento non riuscito: {dettaglio or 'errore di yt-dlp'}")
    return p.stdout


def scarica_url(url: str, cartella: Path) -> dict:
    """→ {file, titolo, data, autore}: scarica il solo audio in cartella/sorgente.m4a."""
    meta = json.loads(_ytdlp(["--dump-single-json", "--no-download", url], TIMEOUT_METADATI_S))
    _ytdlp(["-f", "bestaudio/best", "-x", "--audio-format", "m4a",
            "-o", str(cartella / "sorgente.%(ext)s"), url], TIMEOUT_DOWNLOAD_S)
    f = cartella / "sorgente.m4a"
    if not f.is_file():
        trovati = sorted(cartella.glob("sorgente.*"))
        if not trovati:
            raise RuntimeError("Lo scaricamento non ha prodotto alcun file")
        f = trovati[0]
    d = meta.get("upload_date") or ""
    return {
        "file": f.name,
        "titolo": (meta.get("title") or "").strip()[:250],
        "data": f"{d[6:8]}/{d[4:6]}/{d[:4]}" if len(d) == 8 else "",
        "autore": meta.get("uploader") or meta.get("channel") or "",
        "url": url,
    }


def _ffmpeg(args: list[str]) -> None:
    p = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("ffmpeg non riesce a leggere il file: " + (p.stderr.strip().splitlines() or ["formato non supportato"])[-1])


def durata_s(percorso: Path) -> float:
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                        str(percorso)], capture_output=True, text=True)
    try:
        return float(p.stdout.strip())
    except ValueError:
        return 0.0


def prepara_audio(sorgente: Path, cartella: Path) -> tuple[Path, float]:
    """Sorgente (audio o video) → audio.m4a mono per l'ascolto nell'interfaccia."""
    dest = cartella / "audio.m4a"
    tmp = cartella / "audio.parziale.m4a"  # il lettore non deve mai vedere un file a metà
    _ffmpeg(["-i", str(sorgente), "-vn", "-ac", "1", "-c:a", "aac", "-b:a", "96k", str(tmp)])
    os.replace(tmp, dest)
    return dest, durata_s(dest)


@contextmanager
def wav_temporaneo(audio: Path):
    """WAV 16 kHz mono temporaneo per i motori, rimosso a fine fase."""
    fd, wav = tempfile.mkstemp(suffix=".wav", prefix="sbob_")
    os.close(fd)
    try:
        _ffmpeg(["-i", str(audio), "-ac", "1", "-ar", "16000", "-vn", wav])
        yield wav
    finally:
        with contextlib.suppress(OSError):
            os.remove(wav)
