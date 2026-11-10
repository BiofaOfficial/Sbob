# Security

## Threat model

Sbob is a **single-user, local-only** application. It has no login by design, so its protection is
that it only answers the computer it runs on:

- The server binds to `127.0.0.1` only.
- Every request is checked: a `Host` header that is not `localhost` / `127.0.0.1` / `::1` is rejected
  (DNS rebinding), and so is an `Origin` header pointing to another site (cross-site requests from a
  web page open in your browser).
- The Hugging Face token lives only in `~/Sbob/config.toml` (mode `600`) and is never returned by the API.
- Recordings, transcripts and products never leave the machine. The only outbound traffic is model
  downloads (Hugging Face, Ollama) and the links you explicitly ask Sbob to fetch (yt-dlp).

**Do not expose Sbob to a network** (reverse proxy, port forwarding, `0.0.0.0`): it is not built for it.

## Reporting a vulnerability

Please do **not** open a public issue. Use GitHub's
[private vulnerability reporting](https://github.com/BiofaOfficial/Sbob/security/advisories/new)
and include steps to reproduce. You should get an answer within a week.

Only the latest release is supported.
