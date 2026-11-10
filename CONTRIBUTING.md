# Contributing

Thanks for your interest in Sbob. Issues and pull requests are welcome, in English or Italian.

## Setup

You need [uv](https://docs.astral.sh/uv/) and ffmpeg; Node 20+ only if you touch the frontend.
Tests use fake engines, so they run on Linux and on any Mac without downloading models.

```
./sbob-dev.sh test     # pytest
./sbob-dev.sh lint     # ruff
./sbob-dev.sh run      # run from source with the real engines (Apple Silicon or Linux)
./sbob-dev.sh build    # rebuild the frontend into sbob/static
uvx pre-commit install # optional: ruff + secret scan before each commit
```

## Conventions

- **Code identifiers and comments are in Italian** (`lavoro`, `fase`, `voci`…): keep new code consistent.
- Keep it small: no new dependency or abstraction without a concrete need.
- Every behaviour change comes with a test. CI must be green (ruff, pytest, frontend build, gitleaks).
- UI strings go through `frontend/src/i18n.js`, always in both Italian and English.
- `sbob/static/` is the compiled frontend: never edit it by hand; it is rebuilt at release time.
- Never commit recordings, databases, `config.toml` or tokens.

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
