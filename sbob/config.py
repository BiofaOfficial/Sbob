"""Cartella dati, config.toml e scelta dei motori.

I dati stanno fuori dal codice, in ~/Sbob (override con SBOB_HOME). Il token
Hugging Face vive solo in ~/Sbob/config.toml, mai nel repo.
"""
from __future__ import annotations

import contextlib
import importlib.util
import os
import platform
import sys
import tomllib
from pathlib import Path

import tomli_w

WHISPER_MAC = "mlx-community/whisper-large-v3-turbo"
WHISPER_LINUX = "large-v3-turbo"  # nome faster-whisper


def _linux() -> bool:
    return sys.platform.startswith("linux")


DEFAULTS: dict = {
    "lingua_ui": "",  # "" = la suggerisce il browser
    "whisper_modello": WHISPER_LINUX if _linux() else WHISPER_MAC,
    "llm_modello": "qwen2.5:14b",
    "llm_ctx": 16384,
    "ollama_url": "http://127.0.0.1:11434",
    "porta": 8765,
    "motori": "auto",  # auto | mac | linux | fake
    "hf_token": "",
    "vocabolario_globale": "",  # termini attesi validi per tutti i lavori
    "timeout_fase_s": 4 * 3600,
}


def home() -> Path:
    p = Path(os.environ.get("SBOB_HOME") or (Path.home() / "Sbob"))
    (p / "lavori").mkdir(parents=True, exist_ok=True)
    return p


def percorso_config() -> Path:
    return home() / "config.toml"


def carica() -> dict:
    cfg = dict(DEFAULTS)
    p = percorso_config()
    if p.is_file():
        with p.open("rb") as f:
            cfg.update({k: v for k, v in tomllib.load(f).items() if k in DEFAULTS})
    return cfg


def salva(cfg: dict) -> None:
    p = percorso_config()
    dati = {k: cfg.get(k, v) for k, v in DEFAULTS.items()}
    p.write_text(tomli_w.dumps(dati), encoding="utf-8")
    with contextlib.suppress(OSError):
        os.chmod(p, 0o600)  # contiene il token HF


def motori_effettivi(cfg: dict) -> str:
    m = os.environ.get("SBOB_MOTORI") or cfg.get("motori", "auto")
    if m != "auto":
        return m
    if sys.platform == "darwin" and platform.machine() == "arm64":
        return "mac"
    if _linux() and importlib.util.find_spec("faster_whisper") is not None:
        return "linux"
    return "fake"
