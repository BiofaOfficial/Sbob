#!/bin/bash
# Installa (o aggiorna) Sbob su Ubuntu 22.04 o successivo (e derivate con apt).
# Uso: apri il Terminale nella cartella di Sbob e incolla:   ./install-linux.sh
# Con una scheda NVIDIA (driver già installati) Sbob la usa da solo; senza, lavora sulla CPU (più lento).
set -euo pipefail

SORGENTE="$(cd "$(dirname "$0")" && pwd)"
APP="${XDG_DATA_HOME:-$HOME/.local/share}/sbob/app"
DATI="${SBOB_HOME:-$HOME/Sbob}"
WHISPER_DEFAULT="large-v3-turbo"

verde() { printf "\n\033[1;32m▶ %s\033[0m\n" "$1"; }
giallo() { printf "\033[1;33m! %s\033[0m\n" "$1"; }
errore() { printf "\n\033[1;31m✗ %s\033[0m\n" "$1"; exit 1; }
ollama_risponde() { curl -s -m 3 http://127.0.0.1:11434/api/tags >/dev/null; }

verde "1/5 Controllo del computer"
[ "$(uname -s)" = "Linux" ] || errore "Questo installer è per Linux: su Mac usa ./install.sh"
case "$(uname -m)" in x86_64|aarch64) ;; *) errore "Processore non supportato: $(uname -m)";; esac
command -v apt-get >/dev/null 2>&1 || errore "Serve una distribuzione con apt (Ubuntu, Debian, Mint…)."
RAM_GB="$(awk '/MemTotal/ {printf "%d", $2/1024/1024 + 0.5}' /proc/meminfo)"
[ "$RAM_GB" -ge 15 ] || giallo "Memoria: ${RAM_GB} GB. Sbob ne vorrebbe almeno 16: funzionerà, ma con fatica."
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
  GPU=1; LLM_DEFAULT="qwen2.5:14b"
  echo "Scheda NVIDIA trovata: $(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)"
else
  GPU=0; LLM_DEFAULT="qwen2.5:7b"  # sulla CPU un modello più leggero resta usabile
  giallo "Nessuna scheda NVIDIA: Sbob lavorerà sulla CPU. Funziona, ma è parecchio più lento."
fi
echo "Linux $(uname -m), ${RAM_GB} GB di memoria: ok"

verde "2/5 Strumenti di base (ffmpeg, uv, Ollama)"
MANCANTI=()
for p in ffmpeg curl rsync; do command -v "$p" >/dev/null 2>&1 || MANCANTI+=("$p"); done
if [ "${#MANCANTI[@]}" -gt 0 ]; then
  echo "Installo ${MANCANTI[*]} (serve la password di amministratore)"
  sudo apt-get update -qq && sudo apt-get install -y -qq "${MANCANTI[@]}"
fi
export PATH="$HOME/.local/bin:$PATH"
command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
command -v uv >/dev/null 2>&1 || errore "uv non si è installato: chiudi e riapri il Terminale, poi rilancia ./install-linux.sh"
if ! command -v ollama >/dev/null 2>&1; then
  echo "Installo Ollama (serve la password di amministratore)"
  curl -fsSL https://ollama.com/install.sh | sh
fi
if ! ollama_risponde; then
  sudo systemctl start ollama 2>/dev/null || (nohup ollama serve >/dev/null 2>&1 &)
  for _ in $(seq 1 20); do ollama_risponde && break; sleep 1; done
fi
ollama_risponde || errore "Ollama non parte: prova «sudo systemctl start ollama» e rilancia ./install-linux.sh"

verde "3/5 Copia di Sbob e ambiente Python (il primo download è grande: alcuni GB)"
mkdir -p "$APP" "$DATI"
rsync -a --delete --exclude .git --exclude .github --exclude _privato --exclude tests --exclude .venv \
  --exclude node_modules --exclude frontend --exclude '__pycache__' "$SORGENTE/" "$APP/"
cd "$APP"
EXTRA=(--extra linux --extra voci)  # voci: si attivano poi inserendo il token in Impostazioni
uv sync --frozen "${EXTRA[@]}" -q || uv sync "${EXTRA[@]}" -q

verde "4/5 Modelli (il primo download può richiedere parecchi minuti)"
# aggiornamento: si tengono i modelli scelti in Impostazioni; SBOB_LLM forza un modello diverso
read -r LLM WHISPER < <(uv run --no-sync python -c "
from sbob import config
c = config.carica() if config.percorso_config().is_file() else {}
print(c.get('llm_modello') or '$LLM_DEFAULT', c.get('whisper_modello') or '$WHISPER_DEFAULT')")
LLM="${SBOB_LLM:-$LLM}"
uv run --no-sync python -c "from faster_whisper import download_model as d; d('$WHISPER')"
ollama pull "$LLM"
uv run --no-sync python - "$LLM" "$WHISPER" <<'PY'
import sys
from sbob import config
cfg = config.carica()
cfg["llm_modello"], cfg["whisper_modello"] = sys.argv[1], sys.argv[2]
config.salva(cfg)
PY

verde "5/5 Avvio dal menu delle applicazioni"
UV="$(command -v uv)"
# le librerie CUDA arrivano con PyTorch: faster-whisper le trova solo se sono nel percorso delle librerie
LIB_NVIDIA=""
if [ "$GPU" = 1 ]; then
  LIB_NVIDIA="$(uv run --no-sync python -c "
import glob, os, nvidia
print(':'.join(sorted(glob.glob(os.path.join(list(nvidia.__path__)[0], '*', 'lib')))))" 2>/dev/null || true)"
fi
# avvio in sottofondo: niente finestra del Terminale; il log va in $DATI/sbob.log
cat > "$APP/avvia.sh" <<CMD
#!/bin/bash
export PATH="\$HOME/.local/bin:/usr/local/bin:\$PATH"
${LIB_NVIDIA:+export LD_LIBRARY_PATH="$LIB_NVIDIA\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH}"}
cd "$APP" || exit 1
nohup "$UV" run --no-sync python -m sbob >> "$DATI/sbob.log" 2>&1 &
CMD
chmod +x "$APP/avvia.sh"
MENU="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$MENU"
cat > "$MENU/sbob.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=Sbob
Comment=Da una registrazione a materiale di studio, tutto in locale
Comment[en]=From a recording to study material, all on your computer
Exec="$APP/avvia.sh"
Icon=$APP/logo-b-tile.svg
Terminal=false
Categories=Education;AudioVideo;
DESK
chmod +x "$MENU/sbob.desktop"
SCRIVANIA="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
if [ -d "$SCRIVANIA" ]; then
  cp "$MENU/sbob.desktop" "$SCRIVANIA/sbob.desktop"
  gio set "$SCRIVANIA/sbob.desktop" metadata::trusted true 2>/dev/null || true  # GNOME: «Consenti avvio»
fi
update-desktop-database "$MENU" 2>/dev/null || true

verde "Fatto! Cerca «Sbob» tra le applicazioni (o usa l'icona sulla Scrivania): si apre il browser."
echo "Se l'icona sulla Scrivania non parte: clic destro → «Consenti avvio»."
echo "Per chiudere Sbob usa «Esci» nella barra a sinistra della pagina."
