#!/bin/bash
# deploy.sh — Deploy da aplicacao de energia para o Unraid
#
# USO:
#   ./deploy.sh
#   UNRAID_HOST=192.168.122.110 ./deploy.sh  # se 'unraid' nao resolver via SSH config
#
# PRE-REQUISITOS:
#   - SSH configurado para o Unraid sem password (chave SSH em ~/.ssh/authorized_keys no Unraid)
#   - Testar: ssh unraid 'echo OK'
#   - rsync instalado localmente: which rsync
#
# O que este script faz:
#   1. Sincroniza o codigo fonte para /mnt/user/appdata/energia/app/ no Unraid
#   2. Copia nginx/energia.conf para /mnt/user/appdata/nginx/conf.d/
#   3. Faz build e restart do container Docker no Unraid
#   4. Faz reload do nginx para aplicar a nova config
#   5. Verifica o health check da aplicacao

set -euo pipefail

UNRAID_HOST="${UNRAID_HOST:-unraid}"
DEPLOY_DIR="/mnt/user/appdata/energia"
NGINX_CONF_DIR="/mnt/user/appdata/nginx/conf.d"

echo "=== Deploy Energia Monitor para $UNRAID_HOST ==="
echo ""

# 1. Sincronizar codigo fonte
echo "[1/5] A sincronizar codigo para $UNRAID_HOST:$DEPLOY_DIR/app/ ..."
rsync -avz --delete \
  --exclude '.git/' \
  --exclude '.planning/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '*.pyo' \
  --exclude 'data/' \
  --exclude 'state/' \
  --exclude '.env' \
  --exclude 'venv/' \
  --exclude '.venv/' \
  --exclude 'node_modules/' \
  ./ "$UNRAID_HOST:$DEPLOY_DIR/app/"

# 2. Copiar config nginx
echo ""
echo "[2/5] A copiar nginx/energia.conf para $UNRAID_HOST:$NGINX_CONF_DIR/ ..."
# Criar directoria conf.d se nao existir
ssh "$UNRAID_HOST" "mkdir -p $NGINX_CONF_DIR"
rsync -avz nginx/energia.conf "$UNRAID_HOST:$NGINX_CONF_DIR/energia.conf"

# 3. Build e restart do container
echo ""
echo "[3/5] A fazer build e restart do container no Unraid ..."
# Criar directoria de dados se nao existir
ssh "$UNRAID_HOST" "mkdir -p $DEPLOY_DIR/data"
ssh "$UNRAID_HOST" "cd $DEPLOY_DIR/app && docker compose -f docker-compose.prod.yml up -d --build"

# 4. Reload nginx
echo ""
echo "[4/5] A fazer reload do nginx ..."
# Tentar varios nomes possiveis para o container nginx no Unraid
ssh "$UNRAID_HOST" "
  NGINX_CONTAINER=\$(docker ps --format '{{.Names}}' | grep -i nginx | head -1)
  if [ -n \"\$NGINX_CONTAINER\" ]; then
    echo \"Container nginx encontrado: \$NGINX_CONTAINER\"
    docker exec \"\$NGINX_CONTAINER\" nginx -s reload && echo 'OK: nginx recarregado' || echo 'AVISO: nginx reload falhou'
  else
    echo 'AVISO: Container nginx nao encontrado — verificar manualmente com: docker ps'
    echo 'Para recarregar manualmente: docker exec <nome-container-nginx> nginx -s reload'
  fi
"

# 5. Verificar health
echo ""
echo "[5/5] A verificar health da aplicacao ..."
echo "A aguardar arranque do container (10s)..."
sleep 10
ssh "$UNRAID_HOST" "
  # Tentar porta 8001 (porta exposta no host pelo docker-compose.prod.yml)
  if curl -sf http://localhost:8001/health > /dev/null 2>&1; then
    echo 'OK: Health check passou (porta 8001)'
  else
    echo 'AVISO: Health check falhou na porta 8001'
    echo 'A verificar logs do container...'
    cd $DEPLOY_DIR/app && docker compose -f docker-compose.prod.yml logs --tail=20
  fi
" && true

echo ""
echo "=== Deploy completo ==="
echo ""
echo "URLs de acesso:"
echo "  Local:     http://192.168.122.110:8090/hobbies/casa/energia/"
TAILSCALE_IP=$(ssh "$UNRAID_HOST" 'tailscale ip -4 2>/dev/null' 2>/dev/null || echo "TAILSCALE_IP")
echo "  Tailscale: http://$TAILSCALE_IP:8090/hobbies/casa/energia/"
echo ""
echo "Se o nginx nao tiver conf.d/ include, copiar manualmente nginx/energia.conf"
echo "para o server block em nginx.conf do Unraid."
echo ""
echo "Em caso de problemas:"
echo "  ssh $UNRAID_HOST 'cd $DEPLOY_DIR/app && docker compose -f docker-compose.prod.yml logs'"
