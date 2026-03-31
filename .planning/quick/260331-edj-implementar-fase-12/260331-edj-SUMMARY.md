---
phase: quick
plan: 260331-edj
subsystem: deploy
tags: [deploy, nginx, docker, reverse-proxy, homepage]
dependency_graph:
  requires: []
  provides: [docker-compose.prod.yml, nginx/energia.conf, deploy.sh, homepage/energia-widget.yaml]
  affects: [src/web/app.py, entrypoint.sh]
tech_stack:
  added: []
  patterns: [FastAPI root_path, nginx reverse proxy strip prefix, rsync deploy]
key_files:
  created:
    - docker-compose.prod.yml
    - nginx/energia.conf
    - deploy.sh
    - homepage/energia-widget.yaml
  modified:
    - src/web/app.py
    - entrypoint.sh
decisions:
  - "Expor porta 8001 no host Unraid (pragmatico) em vez de rede Docker partilhada — evita complexidade de redes e funciona sempre"
  - "ROOT_PATH definido em dois lugares (FastAPI constructor + uvicorn --root-path) como belt-and-suspenders"
  - "homepage/energia-widget.yaml recomenda variante simples (sem iframe) para evitar problemas CORS/CSP"
metrics:
  duration_seconds: 130
  completed_date: "2026-03-31"
  tasks_completed: 2
  tasks_total: 3
  files_modified: 6
---

# Quick Task 260331-edj: Deploy Unraid — nginx reverse proxy + Homepage + deploy script

**One-liner:** FastAPI com ROOT_PATH para reverse proxy em /hobbies/casa/energia/, docker-compose.prod.yml para Unraid, nginx config, deploy.sh one-command e Homepage widget.

## Tasks Executadas

| # | Nome | Commit | Estado |
|---|------|--------|--------|
| 1 | Configurar root_path FastAPI + docker-compose.prod.yml + nginx reverse proxy | 01d1e37 | Completo |
| 2 | Script de deploy + Homepage widget | 48c99ec | Completo |
| 3 | Checkpoint: verificar deploy no Unraid | — | **NAO EXECUTADO (checkpoint:human-verify)** |

## Artefactos Criados

### docker-compose.prod.yml
Compose de producao para o Unraid:
- Container `energia-monitor` com porta 8001 exposta no host
- Volume para `/mnt/user/appdata/energia/data`
- `ROOT_PATH=/hobbies/casa/energia` definido como env var
- `restart: unless-stopped`

### nginx/energia.conf
Configuracao de reverse proxy para o nginx do Unraid:
- `location /hobbies/casa/energia/` com `proxy_pass http://127.0.0.1:8001/`
- Trailing slash no proxy_pass para strip do prefixo
- Headers `X-Forwarded-*` correctos
- Instrucoes de instalacao detalhadas nos comentarios

### deploy.sh
Script executavel one-command:
1. rsync do codigo (excluindo .git, .planning, data, __pycache__)
2. Copia nginx/energia.conf para conf.d/ no Unraid
3. Build e restart do container Docker
4. Reload do nginx (detecta nome do container automaticamente)
5. Health check com feedback e logs em caso de falha

### homepage/energia-widget.yaml
Snippet YAML para o Homepage do Unraid com tres variantes:
- Opcao 1 (recomendada): tile simples com link e icone
- Opcao 2: tile com iframe (comentada)
- Opcao Tailscale: para acesso remoto (comentada)

## Alteracoes a Ficheiros Existentes

### src/web/app.py
```python
ROOT_PATH = os.environ.get("ROOT_PATH", "")
app = FastAPI(title="Monitorizacao Eletricidade", lifespan=lifespan, root_path=ROOT_PATH)
```
Os templates ja usavam `url_for('static', ...)` — nenhuma alteracao necessaria nos templates.

### entrypoint.sh
Adicionado `--root-path "$ROOT_PATH"` ao comando uvicorn como redundancia.

## Checkpoint Pendente

A Task 3 e um `checkpoint:human-verify` que requer:
1. SSH para o Unraid e verificar configuracao nginx
2. Executar `./deploy.sh` (primeiro deploy)
3. Testar acesso em http://192.168.122.110:8090/hobbies/casa/energia/
4. Configurar tile no Homepage
5. Testar acesso Tailscale

**Para executar o deploy:**
```bash
cd /Users/ricmag/Documents/AI/3-hobbies/Casa/energia/monitorizacao-eletricidade
./deploy.sh
```

Se o nginx do Unraid nao tiver conf.d/ include, copiar manualmente o bloco `location` de `nginx/energia.conf` para o server block existente em nginx.conf.

## Decisoes

1. **Porta 8001 em vez de rede Docker partilhada** — A abordagem pragmatica (expor porta no host) evita complexidade de redes Docker e funciona independentemente da configuracao do nginx no Unraid. Documentado como "DECISAO PRAGMATICA" no plan.

2. **ROOT_PATH em dois lugares** — Definido tanto no constructor FastAPI como no uvicorn como belt-and-suspenders. O FastAPI usa para gerar URLs correctos; o uvicorn para comunicar ao ASGI.

3. **Homepage: variante simples recomendada** — iframe pode causar problemas CORS/CSP; tile simples e mais robusto.

## Deviations from Plan

None — plano executado exactamente como escrito. A unica decisao de implementacao (porta 8001 vs rede Docker) estava documentada no plan como "DECISAO PRAGMATICA".

## Verificacao

```
OK: root_path configurado correctamente
OK: docker-compose.prod.yml existe
OK: nginx/energia.conf existe
OK: deploy.sh executavel
OK: homepage widget existe
OK: deploy.sh syntax valida
126 passed, 14 skipped in 1.01s (testes existentes)
```

## Self-Check: PASSED

Ficheiros criados verificados:
- docker-compose.prod.yml: FOUND
- nginx/energia.conf: FOUND
- deploy.sh: FOUND (executavel)
- homepage/energia-widget.yaml: FOUND

Commits verificados:
- 01d1e37: FOUND (Task 1)
- 48c99ec: FOUND (Task 2)
