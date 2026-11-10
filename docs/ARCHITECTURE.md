# Architecture

Sbob is one Python process: a FastAPI server that also serves the compiled React frontend and runs
a background worker. Everything is local; state lives in `~/Sbob` (override with `SBOB_HOME`).

```
browser ──HTTP 127.0.0.1──▶ FastAPI (sbob/api.py) ──▶ SQLite (sbob/db.py)
                                   │                        ▲
                                   └── Worker (sbob/worker.py) ── phases (sbob/pipeline/) ── engines (sbob/engines/)
```

## Modules

| Path | Role |
|---|---|
| `sbob/__main__.py` | CLI: start the server and open the browser, or `check` the real engines |
| `sbob/api.py` | REST API, local-only guard (Host/Origin), static frontend |
| `sbob/db.py` | SQLite schema, migrations via `PRAGMA user_version`, one connection per operation |
| `sbob/worker.py` | Job queue: one phase at a time, resume after restart, per-phase timeout, `caffeinate` |
| `sbob/pipeline/fasi.py` | The phases, their dependency graph and execution |
| `sbob/pipeline/acquisizione.py` | yt-dlp download, ffmpeg audio preparation |
| `sbob/pipeline/mapreduce.py` | Splits the transcript in ~1300-word blocks and reduces notes within the context budget |
| `sbob/engines/` | Swappable engines behind small protocols (`base.py`): transcription, diarization, LLM |
| `sbob/profili.py`, `sbob/prompts_studio.py` | Profiles (lecture, meeting, interview, two-party) and prompts, IT/EN |
| `sbob/export/` | Markdown, PDF (ReportLab) and Anki export |
| `frontend/` | React + Vite source; built into `sbob/static/` |

## Pipeline

Each job is a row in `lavori` plus one row per phase in `fasi`. A phase runs only when all its
ancestors are done or skipped; re-queuing a phase re-queues what depends on it.

```
acquisizione → audio → trascrizione → voci → note ─┬─ prodotto
                                                   ├─ mappa, flashcard, autoverifica, glossario
                                                   └─ dispensa (on request)
```

- `voci` (speaker diarization) is skipped unless enabled; it needs a Hugging Face token.
- `note` is the map step (one LLM call per block); every product is a reduce over the notes.
- Structured products (flashcards, quiz, glossary) are validated with Pydantic; one retry on invalid JSON.
- Only one model is kept in memory at a time: the worker unloads an engine before loading another.

## Engines

`engines.crea()` picks the set at startup: `mac` (mlx-whisper, pyannote, Ollama) on Apple Silicon,
`fake` elsewhere and in tests (`SBOB_MOTORI=fake`). Adding a platform means adding an engine set,
not touching the pipeline.

## Data

`~/Sbob/sbob.db` (history), `~/Sbob/lavori/<id>/` (source file and extracted audio),
`~/Sbob/config.toml` (settings and token, mode 600), `~/Sbob/sbob.log`.

## Security

See [`SECURITY.md`](../SECURITY.md).
