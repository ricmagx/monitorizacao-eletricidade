---
phase: 12-deploy-unraid-homepage-tailscale
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docker-compose.yml
  - docker-compose.prod.yml
  - entrypoint.sh
  - src/web/app.py
  - deploy.sh
  - nginx/energia.conf
  - homepage/energia-widget.yaml
autonomous: false
requirements: [INFRA-02, INFRA-04, INFRA-05]

must_haves:
  truths:
    - "A aplicacao responde em http://192.168.122.110:8090/hobbies/casa/energia/ a partir da rede local"
    - "Um tile Energia aparece no Homepage do Unraid e abre a aplicacao ao clicar"
    - "A aplicacao esta acessivel via Tailscale fora da rede local"
    - "O comando deploy.sh a partir do Mac copia ficheiros e reinicia o container no Unraid"
  artifacts:
    - path: "docker-compose.prod.yml"
      provides: "Compose de producao com rede nginx e volume correcto"
    - path: "deploy.sh"
      provides: "Script de deploy rsync+SSH one-command"
    - path: "nginx/energia.conf"
      provides: "Configuracao nginx reverse proxy para /hobbies/casa/energia/"
    - path: "homepage/energia-widget.yaml"
      provides: "Snippet YAML para Homepage tile"
  key_links:
    - from: "nginx/energia.conf"
      to: "docker container energia:8000"
      via: "proxy_pass com strip de prefix"
      pattern: "proxy_pass.*http.*energia.*8000"
    - from: "deploy.sh"
      to: "unraid:/mnt/user/appdata/"
      via: "rsync over SSH"
      pattern: "rsync.*unraid"
    - from: "src/web/app.py"
      to: "nginx/energia.conf"
      via: "root_path FastAPI para gerar URLs correctos atras do proxy"
      pattern: "root_path"
---

<objective>
Deploy da aplicacao de monitorizacao de electricidade no Unraid, com nginx reverse proxy em /hobbies/casa/energia/, tile no Homepage, e acesso Tailscale.

Purpose: Colocar a aplicacao em producao no servidor 24/7 do utilizador, acessivel local e remotamente.
Output: docker-compose.prod.yml, nginx config, deploy script, homepage widget config, e documentacao de deploy.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@docker-compose.yml
@Dockerfile
@entrypoint.sh
@src/web/app.py
@config/system.json

<interfaces>
<!-- Existing app structure -->

From src/web/app.py:
```python
app = FastAPI(...)  # Mounts static at /static, templates in src/web/templates
PROJECT_ROOT = Path(os.environ.get("APP_ROOT", str(BASE_DIR.parent.parent)))
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
```

From docker-compose.yml:
```yaml
services:
  energia:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - energia_data:/app/data
    environment:
      - DB_PATH=/app/data/energia.db
```

From entrypoint.sh:
```sh
alembic upgrade head
exec uvicorn src.web.app:app --host 0.0.0.0 --port 8000
```

Infrastructure context:
- Unraid nginx: http://192.168.122.110:8090 (already running, serves /mnt/user/appdata/nginx/www/)
- Unraid Homepage: http://192.168.122.110:3000
- Tailscale: already active on Unraid
- Deploy target: unraid:/mnt/user/appdata/
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Configurar root_path FastAPI + docker-compose.prod.yml + nginx reverse proxy</name>
  <files>src/web/app.py, docker-compose.prod.yml, nginx/energia.conf, entrypoint.sh</files>
  <action>
  1. **src/web/app.py** — Adicionar suporte a ROOT_PATH via env var para funcionar atras de reverse proxy:
     - Ler `ROOT_PATH = os.environ.get("ROOT_PATH", "")` 
     - Passar `root_path=ROOT_PATH` ao construtor FastAPI: `app = FastAPI(root_path=ROOT_PATH)`
     - Isto faz com que URLs gerados pelo Jinja2 (url_for) e pela OpenAPI incluam o prefixo /hobbies/casa/energia
     - NAO alterar os mounts de /static — o root_path do FastAPI trata disso automaticamente
     - Verificar templates: se algum template hardcoda "/static/" em vez de usar url_for('static', ...), corrigir para usar o prefixo. Grep por `"/static/` e `'/static/` nos templates e corrigir para `{{ request.scope['root_path'] }}/static/` ou usar url_for

  2. **docker-compose.prod.yml** — Criar compose de producao (separado do dev):
     ```yaml
     services:
       energia:
         build: .
         container_name: energia-monitor
         environment:
           - DB_PATH=/app/data/energia.db
           - ROOT_PATH=/hobbies/casa/energia
         volumes:
           - /mnt/user/appdata/energia/data:/app/data
         networks:
           - nginx_network
         restart: unless-stopped

     networks:
       nginx_network:
         external: true
         name: nginx_default  # ou o nome da rede do nginx existente — verificar com `docker network ls` no Unraid
     ```
     NAO expor portas — o nginx acede via rede Docker interna.
     Nota: o nome da network pode variar. Alternativa se nao houver rede partilhada: usar `network_mode: bridge` e proxy_pass para container IP, ou usar ports e proxy_pass para host IP 127.0.0.1:8000.
     DECISAO PRAGMATICA: Se complicar com redes Docker, expor porta 8001 no host e proxy_pass para http://127.0.0.1:8001. Isto funciona sempre.

  3. **nginx/energia.conf** — Criar ficheiro de configuracao nginx (para copiar para o Unraid):
     ```nginx
     # Adicionar dentro do server block do nginx existente em :8090
     # ou como ficheiro separado em /mnt/user/appdata/nginx/conf.d/
     
     location /hobbies/casa/energia/ {
         proxy_pass http://energia-monitor:8000/;  # trailing slash strips o prefix
         proxy_set_header Host $host;
         proxy_set_header X-Real-IP $remote_addr;
         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
         proxy_set_header X-Forwarded-Proto $scheme;
         proxy_set_header X-Forwarded-Prefix /hobbies/casa/energia;
     }
     ```
     Incluir comentarios com instrucoes de onde colocar este ficheiro no Unraid.
     Se o nginx nao suportar proxy_pass (e.g. e apenas um file server), documentar a alternativa: correr um segundo nginx como reverse proxy ou usar o Nginx Proxy Manager do Unraid.

  4. **entrypoint.sh** — Adicionar `--root-path` ao uvicorn como redundancia (belt-and-suspenders com o FastAPI root_path):
     ```sh
     ROOT_PATH="${ROOT_PATH:-}"
     exec uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --root-path "$ROOT_PATH"
     ```
  </action>
  <verify>
    <automated>cd /Users/ricmag/Documents/AI/3-hobbies/Casa/energia/monitorizacao-eletricidade && python -c "
import os; os.environ['ROOT_PATH']='/hobbies/casa/energia'
from src.web.app import app
assert app.root_path == '/hobbies/casa/energia', f'root_path={app.root_path}'
print('OK: root_path configurado')
" && test -f docker-compose.prod.yml && test -f nginx/energia.conf && echo "OK: ficheiros existem"</automated>
  </verify>
  <done>
  - FastAPI app aceita ROOT_PATH env var e configura root_path correctamente
  - docker-compose.prod.yml existe com volume path do Unraid e ROOT_PATH definido
  - nginx/energia.conf existe com proxy_pass configurado para /hobbies/casa/energia/
  - entrypoint.sh passa --root-path ao uvicorn
  - Templates usam caminhos relativos ao root_path (nao hardcoded /static/)
  </done>
</task>

<task type="auto">
  <name>Task 2: Script de deploy + Homepage widget + documentacao</name>
  <files>deploy.sh, homepage/energia-widget.yaml</files>
  <action>
  1. **deploy.sh** — Criar script executavel de deploy one-command:
     ```bash
     #!/bin/bash
     set -euo pipefail
     
     UNRAID_HOST="${UNRAID_HOST:-unraid}"
     DEPLOY_DIR="/mnt/user/appdata/energia"
     
     echo "=== Deploy Energia Monitor para $UNRAID_HOST ==="
     
     # 1. Sync codigo fonte (excluir dev files, .git, data, __pycache__)
     rsync -avz --delete \
       --exclude '.git/' \
       --exclude '.planning/' \
       --exclude '__pycache__/' \
       --exclude '*.pyc' \
       --exclude 'data/' \
       --exclude 'state/' \
       --exclude '.env' \
       --exclude 'venv/' \
       --exclude '.venv/' \
       ./ "$UNRAID_HOST:$DEPLOY_DIR/app/"
     
     # 2. Copiar nginx config
     rsync -avz nginx/energia.conf "$UNRAID_HOST:/mnt/user/appdata/nginx/conf.d/energia.conf"
     
     # 3. Build e restart container no Unraid
     ssh "$UNRAID_HOST" "cd $DEPLOY_DIR/app && docker compose -f docker-compose.prod.yml up -d --build"
     
     # 4. Reload nginx para aplicar nova config
     ssh "$UNRAID_HOST" "docker exec nginx nginx -s reload 2>/dev/null || echo 'AVISO: nginx reload falhou — verificar nome do container nginx'"
     
     # 5. Verificar health
     echo "A aguardar arranque..."
     sleep 5
     ssh "$UNRAID_HOST" "curl -sf http://localhost:8000/health || curl -sf http://localhost:8001/health" && echo "OK: Health check passed" || echo "AVISO: Health check falhou — verificar logs com: ssh $UNRAID_HOST 'cd $DEPLOY_DIR/app && docker compose -f docker-compose.prod.yml logs'"
     
     echo "=== Deploy completo ==="
     echo "Local:     http://192.168.122.110:8090/hobbies/casa/energia/"
     echo "Tailscale: http://$(ssh $UNRAID_HOST 'tailscale ip -4 2>/dev/null || echo TAILSCALE_IP'):8090/hobbies/casa/energia/"
     ```
     Tornar executavel: chmod +x deploy.sh

  2. **homepage/energia-widget.yaml** — Snippet YAML para o Homepage do Unraid:
     ```yaml
     # Adicionar a services.yaml do Homepage (http://192.168.122.110:3000)
     # Localizacao tipica: /mnt/user/appdata/homepage/config/services.yaml
     
     - Casa:
         - Energia:
             icon: mdi-lightning-bolt
             href: http://192.168.122.110:8090/hobbies/casa/energia/
             description: Monitorizacao de electricidade
             widget:
               type: iframe
               src: http://192.168.122.110:8090/hobbies/casa/energia/
     ```
     Incluir tambem a variante simples (sem widget iframe, apenas link):
     ```yaml
     - Casa:
         - Energia:
             icon: mdi-lightning-bolt
             href: http://192.168.122.110:8090/hobbies/casa/energia/
             description: Monitorizacao de electricidade
     ```
     Documentar no ficheiro: "Copiar o bloco desejado para services.yaml do Homepage. A variante simples (apenas link) e recomendada."
  </action>
  <verify>
    <automated>cd /Users/ricmag/Documents/AI/3-hobbies/Casa/energia/monitorizacao-eletricidade && test -x deploy.sh && echo "OK: deploy.sh executavel" && test -f homepage/energia-widget.yaml && echo "OK: homepage widget existe" && bash -n deploy.sh && echo "OK: deploy.sh syntax valida"</automated>
  </verify>
  <done>
  - deploy.sh existe, e executavel, e tem syntax bash valida
  - deploy.sh faz rsync do codigo, copia nginx config, faz build+restart do container, reload nginx, e verifica health
  - homepage/energia-widget.yaml existe com snippet pronto a copiar para services.yaml do Homepage
  - Ambos os ficheiros incluem comentarios com instrucoes de uso
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
  Deploy completo da aplicacao no Unraid:
  - FastAPI com root_path para funcionar atras de nginx em /hobbies/casa/energia/
  - docker-compose.prod.yml para producao no Unraid
  - nginx reverse proxy config
  - Script de deploy one-command (deploy.sh)
  - Homepage widget config
  </what-built>
  <how-to-verify>
  1. **Verificar configuracao nginx no Unraid:**
     - SSH para o Unraid: `ssh unraid`
     - Verificar como o nginx esta configurado: `docker exec nginx cat /etc/nginx/nginx.conf` (ajustar nome do container)
     - Verificar se suporta conf.d/ includes ou se precisa de edicao manual do nginx.conf
     - Se nao houver conf.d/ include, copiar manualmente o conteudo de nginx/energia.conf para o server block existente

  2. **Executar o primeiro deploy:**
     ```bash
     cd /Users/ricmag/Documents/AI/3-hobbies/Casa/energia/monitorizacao-eletricidade
     ./deploy.sh
     ```
     - Se falhar na rede Docker, editar docker-compose.prod.yml para expor porta 8001 e ajustar nginx config para proxy_pass http://127.0.0.1:8001/

  3. **Testar acesso local:**
     - Abrir http://192.168.122.110:8090/hobbies/casa/energia/ no browser
     - Verificar que a pagina carrega com CSS e JS (static files correctos)
     - Verificar que o selector de local funciona (HTMX)

  4. **Testar Homepage tile:**
     - Copiar conteudo de homepage/energia-widget.yaml para /mnt/user/appdata/homepage/config/services.yaml no Unraid
     - Abrir http://192.168.122.110:3000 e verificar que o tile "Energia" aparece
     - Clicar no tile e verificar que abre a aplicacao

  5. **Testar Tailscale:**
     - No telemovel (fora da rede local, com Tailscale ligado): abrir http://TAILSCALE_IP:8090/hobbies/casa/energia/
     - O IP Tailscale do Unraid pode ser obtido com: `ssh unraid 'tailscale ip -4'`
  </how-to-verify>
  <resume-signal>Escreve "aprovado" se tudo funciona, ou descreve os problemas encontrados</resume-signal>
</task>

</tasks>

<verification>
- `python -c "from src.web.app import app"` sem erros
- docker-compose.prod.yml valido: `docker compose -f docker-compose.prod.yml config` (correr no Unraid apos deploy)
- nginx config valida: `nginx -t` (dentro do container nginx no Unraid)
- deploy.sh executavel e com syntax valida
- Testes existentes continuam a passar: `cd /Users/ricmag/Documents/AI/3-hobbies/Casa/energia/monitorizacao-eletricidade && python -m pytest tests/ -x -q`
</verification>

<success_criteria>
1. A aplicacao responde em http://192.168.122.110:8090/hobbies/casa/energia/ com CSS/JS a carregar correctamente
2. O tile "Energia" aparece no Homepage e abre a aplicacao
3. A aplicacao e acessivel via Tailscale (IP Tailscale do Unraid + porta 8090 + path)
4. `./deploy.sh` a partir do Mac sincroniza codigo, faz build e reinicia a aplicacao no Unraid
</success_criteria>

<output>
After completion, create `.planning/quick/260331-edj-implementar-fase-12/260331-edj-SUMMARY.md`
</output>
