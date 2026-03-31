#!/bin/sh
set -e
cd /app
alembic upgrade head
# ROOT_PATH: prefixo do path quando a aplicacao corre atras de um reverse proxy
# Ex: ROOT_PATH=/hobbies/casa/energia quando nginx faz proxy de /hobbies/casa/energia/ -> app
ROOT_PATH="${ROOT_PATH:-}"
exec uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --root-path "$ROOT_PATH"
