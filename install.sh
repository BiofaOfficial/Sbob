#!/bin/bash
# Installa (o aggiorna) Sbob su un Mac con Apple Silicon.
# Uso: apri il Terminale nella cartella di Sbob e incolla:   ./install.sh
set -euo pipefail

SORGENTE="$(cd "$(dirname "$0")" && pwd)"
APP="$HOME/Library/Application Support/Sbob/app"
DATI="${SBOB_HOME:-$HOME/Sbob}"
LLM_DEFAULT="qwen2.5:14b"
WHISPER_DEFAULT="mlx-community/whisper-large-v3-turbo"

verde() { printf "\n\033[1;32m▶ %s\033[0m\n" "$1"; }
errore() { printf "\n\033[1;31m✗ %s\033[0m\n" "$1"; exit 1; }

verde "1/5 Controllo del Mac"
[ "$(uname -s)" = "Darwin" ] || errore "Sbob v1 funziona solo su macOS."
[ "$(uname -m)" = "arm64" ] || errore "Serve un Mac con chip Apple (M1, M2, M3, M4…)."
MAJOR="$(sw_vers -productVersion | cut -d. -f1)"
[ "$MAJOR" -ge 14 ] || errore "Serve macOS 14 (Sonoma) o successivo: aggiorna il Mac e riprova."
echo "Mac Apple Silicon, macOS $(sw_vers -productVersion): ok"

verde "2/5 Strumenti di base (Homebrew, ffmpeg, Ollama, uv)"
if ! command -v brew >/dev/null 2>&1; then
  [ -x /opt/homebrew/bin/brew ] || /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$(/opt/homebrew/bin/brew shellenv)"
fi
for f in ffmpeg uv ollama; do
  brew list --formula "$f" >/dev/null 2>&1 || command -v "$f" >/dev/null 2>&1 || brew install "$f"
done
if ! curl -s -m 3 http://127.0.0.1:11434/api/tags >/dev/null; then
  brew services start ollama >/dev/null 2>&1 || (nohup ollama serve >/dev/null 2>&1 &)
  for _ in $(seq 1 20); do curl -s -m 2 http://127.0.0.1:11434/api/tags >/dev/null && break; sleep 1; done
fi
curl -s -m 3 http://127.0.0.1:11434/api/tags >/dev/null || errore "Ollama non parte: apri l'app Ollama e rilancia ./install.sh"

verde "3/5 Copia di Sbob e ambiente Python"
mkdir -p "$APP" "$DATI"
rsync -a --delete --exclude .git --exclude .github --exclude _privato --exclude tests --exclude .venv --exclude node_modules --exclude frontend \
  --exclude '__pycache__' "$SORGENTE/" "$APP/"
cd "$APP"
EXTRA=(--extra mac --extra voci)  # voci: si attivano poi inserendo il token in Impostazioni
uv sync --frozen "${EXTRA[@]}" -q || uv sync "${EXTRA[@]}" -q

verde "4/5 Modelli (il primo download può richiedere parecchi minuti)"
# aggiornamento: si tengono i modelli scelti in Impostazioni; SBOB_LLM forza un modello diverso
read -r LLM WHISPER < <(uv run --no-sync python -c "
from sbob import config
c = config.carica() if config.percorso_config().is_file() else {}
print(c.get('llm_modello') or '$LLM_DEFAULT', c.get('whisper_modello') or '$WHISPER_DEFAULT')")
LLM="${SBOB_LLM:-$LLM}"
uv run --no-sync python -c "from huggingface_hub import snapshot_download as s; s('$WHISPER')"
ollama pull "$LLM"
uv run --no-sync python - "$LLM" "$WHISPER" <<'PY'
import sys
from sbob import config
cfg = config.carica()
cfg["llm_modello"], cfg["whisper_modello"] = sys.argv[1], sys.argv[2]
config.salva(cfg)
PY

verde "5/5 App Sbob"
UV="$(command -v uv)"
# avvio in sottofondo: niente finestra del Terminale; il log va in $DATI/sbob.log
cat > "$APP/avvia.sh" <<CMD
#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:\$PATH"
cd "$APP" || exit 1
nohup "$UV" run --no-sync python -m sbob >> "$DATI/sbob.log" 2>&1 &
CMD
chmod +x "$APP/avvia.sh"
mkdir -p "$HOME/Applications"
rm -rf "$HOME/Applications/Sbob.app"
osacompile -o "$HOME/Applications/Sbob.app" -e "do shell script quoted form of \"$APP/avvia.sh\""
# icona: le app di osacompile hanno anche un catalogo (Assets.car) che ha la precedenza sul file .icns
SAPP="$HOME/Applications/Sbob.app"
cp "$APP/macos/Sbob.icns" "$SAPP/Contents/Resources/applet.icns"
rm -f "$SAPP/Contents/Resources/Assets.car"
/usr/libexec/PlistBuddy -c "Delete :CFBundleIconName" "$SAPP/Contents/Info.plist" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Set :CFBundleIconFile applet" "$SAPP/Contents/Info.plist" 2>/dev/null || true
codesign --force --deep --sign - "$SAPP" 2>/dev/null || true  # firma locale, dopo la modifica del pacchetto
touch "$SAPP"
killall Dock Finder 2>/dev/null || true  # rilegge le icone
xattr -dr com.apple.quarantine "$HOME/Applications/Sbob.app" 2>/dev/null || true
rm -f "$HOME/Desktop/Sbob.command" "$HOME/Desktop/Sbob"
ln -s "$HOME/Applications/Sbob.app" "$HOME/Desktop/Sbob"

verde "Fatto! Fai doppio clic su «Sbob» sulla Scrivania (o in Applicazioni): si apre il browser."
echo "Per chiudere Sbob usa «Esci» nella barra a sinistra della pagina."
