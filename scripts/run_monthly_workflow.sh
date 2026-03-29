#!/bin/zsh
set -eu

ROOT="/Users/ricmag/Documents/AI/3-hobbies/Casa/energia/monitorizacao-eletricidade"
cd "$ROOT"

python3 "$ROOT/src/backend/monthly_workflow.py" \
  --config "$ROOT/config/system.json"
