#!/bin/zsh
set -eu

ROOT="/Users/ricmag/Documents/AI/3-hobbies/Casa/energia/monitorizacao-eletricidade"
cd "$ROOT"

python3 "$ROOT/src/backend/process_latest_download.py" \
  --config "$ROOT/config/system.json"
