#!/bin/zsh
set -eu

ROOT="/Users/ricmag/Documents/AI/3-hobbies/Casa/energia/monitorizacao-eletricidade"

python3 "$ROOT/src/backend/eredes_bootstrap_session.py" \
  --storage-state "$ROOT/state/eredes_storage_state.json" \
  --context-output "$ROOT/state/eredes_bootstrap_context.json"
