#!/bin/bash
# Comandi per chi sviluppa Sbob (non servono all'utente finale).
#   ./sbob-dev.sh test      test con motori finti
#   ./sbob-dev.sh lint      controllo del codice (ruff)
#   ./sbob-dev.sh check     verifica i motori veri su questo computer
#   ./sbob-dev.sh run       avvia dal sorgente
#   ./sbob-dev.sh build     ricompila il frontend in sbob/static (serve Node)
#   ./sbob-dev.sh pacchetto [minor|major]
#                           nuova release: compila, prova, alza la versione (1.0.8 → 1.0.9;
#                           minor → 1.1.0; major → 2.0.0), fa il commit e crea ~/Desktop/Sbob-<versione>.zip
set -euo pipefail
cd "$(dirname "$0")"
# motori veri della piattaforma: mlx-whisper su Mac, faster-whisper su Linux
if [ "$(uname -s)" = "Darwin" ]; then MOTORI=(--extra mac --extra voci); else MOTORI=(--extra linux --extra voci); fi
case "${1:-}" in
  test)  uv run --extra dev pytest -q ;;
  lint)  uvx ruff check sbob tests ;;
  check) uv sync "${MOTORI[@]}" -q && uv run python -m sbob check ;;
  run)   uv run "${MOTORI[@]}" python -m sbob ;;
  build) (cd frontend && npm install --no-audit --no-fund && npx vite build) ;;
  pacchetto)
    "$0" build >/dev/null
    "$0" test
    V="$(python3 - "${2:-patch}" <<'PY'
import re, sys
from pathlib import Path
parte = sys.argv[1]
if parte not in ("patch", "minor", "major"):
    sys.exit("uso: pacchetto [minor|major]")
py = Path("pyproject.toml").read_text()
vecchia = re.search(r'^version = "(\d+)\.(\d+)\.(\d+)"', py, re.M)
M, m, p = map(int, vecchia.groups())
M, m, p = (M + 1, 0, 0) if parte == "major" else (M, m + 1, 0) if parte == "minor" else (M, m, p + 1)
v, old = f"{M}.{m}.{p}", ".".join(vecchia.groups())
def sost(file, schema, n=1):
    f = Path(file)
    t, k = re.subn(schema.replace("V", re.escape(old)), lambda x: x.group(0).replace(old, v), f.read_text(), count=n, flags=re.M)
    assert k == n, f"versione non trovata in {file}"
    f.write_text(t)
sost("pyproject.toml", r'^version = "V"')
sost("sbob/__init__.py", r'__version__ = "V"')
sost("frontend/package.json", r'"version": "V"')
sost("frontend/package-lock.json", r'"version": "V"', 2)
sost("uv.lock", r'name = "sbob"\nversion = "V"')
print(v)
PY
)"
    git add -A
    git commit -qm "Sbob $V"
    git archive --format=zip --prefix=Sbob/ -o "$HOME/Desktop/Sbob-$V.zip" HEAD
    echo "Creato $HOME/Desktop/Sbob-$V.zip" ;;
  *) echo "uso: $0 test|lint|check|run|build|pacchetto"; exit 1 ;;
esac
