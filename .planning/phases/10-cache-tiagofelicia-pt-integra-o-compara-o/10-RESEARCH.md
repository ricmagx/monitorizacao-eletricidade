# Phase 10: Cache tiagofelicia.pt + Integração Comparação — Research

**Researched:** 2026-03-31
**Domain:** FastAPI backend + Jinja2 templates + SQLite cache fallback + HTMX badge
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COMP-03 | Dashboard usa cache quando tiagofelicia.pt está indisponível | Cache SQLite (`comparacoes`) já existe com dados; `build_analysis_from_sqlite()` já lê esses dados; o problema é que `_consultar_tiagofelicia_bg` falha silenciosamente sem actualizar o badge nem garantir que o dashboard usa o cache. A rota `/upload/xlsx` já tem o try/except que engole excepções do Playwright — os dados mais recentes do cache ficam na BD e o dashboard já os lê via `build_analysis_from_sqlite()`. A lacuna é conceptual: o utilizador não sabe se está a ver dados frescos ou dados do cache. |
| COMP-04 | Badge indica se dados são frescos ou do cache (com data) | `frescura_badge.html` já existe e mostra `generated_at` e `days_ago`. A lacuna é que o badge não distingue "dados frescos recém-consultados" de "dados que vieram do cache porque o site estava em baixo". O `freshness` dict atual (`is_stale`, `days_ago`, `generated_at`) não tem um campo `source` (fresh vs cached). |
</phase_requirements>

---

## Summary

Phase 10 é essencialmente uma **melhoria de transparência e resiliência** — o mecanismo de cache já existe desde a Phase 5 (tabela `comparacoes` com `cached_at`), e o fallback para dados em cache já funciona implicitamente (o dashboard lê sempre de SQLite). O que falta é: (1) uma distinção explícita entre "dados acabados de consultar" e "dados do cache porque o site estava em baixo", e (2) garantia de que o utilizador nunca vê uma página de erro nem fica sem ranking quando tiagofelicia.pt está inacessível.

A fase não requer nova infraestrutura. Os três componentes a tocar são: `_consultar_tiagofelicia_bg` (upload.py) para registar se a consulta falhou, `get_freshness_from_sqlite` / `freshness` dict (data_loader.py) para adicionar campo `source`, e `frescura_badge.html` para mostrar visualmente "Frescos" vs "Do cache (data)".

**Primary recommendation:** Adicionar campo `source` ao dict `freshness` retornado por `get_freshness_from_sqlite`, alimentado por uma nova coluna `fetch_status` (ou lógica de comparação de timestamps) na tabela `comparacoes`. Actualizar `frescura_badge.html` com dois estados visuais distintos.

---

## Standard Stack

### Core (já em uso no projecto)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | instalado | Backend HTTP + BackgroundTasks | escolha do projecto |
| SQLAlchemy Core | instalado | Acesso SQLite (tabela comparacoes) | já usado em todas as fases |
| Jinja2 | instalado | Templates HTML | já usado |
| HTMX | CDN | Troca parcial de DOM (badge) | já usado no projecto |
| pytest + TestClient | instalado | Testes | já configurado |

### Sem dependências novas

Esta fase não requer instalar nada. Todas as ferramentas já existem.

---

## Architecture Patterns

### Estado actual do sistema (o que já existe)

```
src/
├── web/
│   ├── routes/upload.py              # _consultar_tiagofelicia_bg — já faz try/except
│   ├── services/data_loader.py       # get_freshness_from_sqlite — já calcula days_ago
│   └── templates/partials/
│       └── frescura_badge.html       # já existe, mas não tem estado "cache"
├── db/schema.py                      # tabela comparacoes — tem cached_at
tests/
├── test_web_dashboard.py             # 29 testes a passar — não tocar
└── conftest.py                       # fixtures web_client, web_client_sqlite
```

### Lacuna exacta (o que falta)

O `freshness` dict retornado por `get_freshness_from_sqlite` tem:
```python
{
    "days_ago": int | None,
    "is_stale": bool,
    "generated_at": str | None,
}
```

Falta o campo `source` para distinguir:
- `"fresh"` — a última consulta a tiagofelicia.pt foi bem-sucedida
- `"cache"` — tiagofelicia.pt estava indisponível; dados são do cache

### Padrão 1: Adicionar coluna `fetch_status` à tabela `comparacoes`

**O que é:** Coluna `TEXT` nullable na tabela `comparacoes` com valores `"ok"` ou `"error"`.
Quando a consulta a tiagofelicia.pt tem sucesso, `fetch_status = "ok"`. Quando falha e os dados já existem no cache, não se insere nada novo (ON CONFLICT DO NOTHING já garante isso).

**Implicação:** A migration Alembic (migration 003) adiciona a coluna. Rows antigas ficam com `NULL` — tratado como `"cache"` no `get_freshness_from_sqlite`.

**Alternativa mais simples (sem migration):** Não adicionar coluna. Em vez disso, `_consultar_tiagofelicia_bg` actualiza o `cached_at` sempre que a consulta tem sucesso — mesmo que o `top_3_json` seja o mesmo. Se `cached_at` é recente (< 24h), `source = "fresh"`. Se é antigo, `source = "cache"`.

**Recomendação: abordagem sem migration** — actualizar `cached_at` na tabela quando a consulta tem sucesso (mesmo sem mudança de dados), usando `ON CONFLICT DO UPDATE SET cached_at = now()`. Desta forma, `cached_at` recente = dados frescos; `cached_at` antigo = dados do cache. Não requer nova coluna nem migration.

### Padrão 2: ON CONFLICT DO UPDATE (upsert com timestamp)

O `_consultar_tiagofelicia_bg` actual usa `on_conflict_do_nothing`. Para COMP-03/04, mudar para `on_conflict_do_update` que actualiza `cached_at` (e os dados) quando a consulta tem sucesso:

```python
# Abordagem actual (Phase 7):
stmt = sqlite_insert(comparacoes).values(...).on_conflict_do_nothing(...)

# Abordagem Phase 10:
stmt = sqlite_insert(comparacoes).values(...).on_conflict_do_update(
    index_elements=["location_id", "year_month"],
    set_={
        "top_3_json": ...,
        "current_supplier_result_json": ...,
        "generated_at": ...,
        "cached_at": datetime.now(timezone.utc),
        "fetch_status": "ok",  # se adicionar coluna
    }
)
```

**Nota:** `on_conflict_do_update` do SQLite dialect (`sqlalchemy.dialects.sqlite`) já está importado em `upload.py` — só mudar `do_nothing` para `do_update`.

### Padrão 3: Threshold "fresh" no badge

`FRESH_THRESHOLD_HOURS = 48` — se `cached_at` < 48h, badge verde "Dados frescos (data)". Se >= 48h, badge amarelo "Do cache — última consulta: data". Se nenhum dado, badge vermelho "Sem dados".

**Onde calcular:** `get_freshness_from_sqlite` em `data_loader.py`. Adicionar campo `source` ao dict retornado.

### Padrão 4: Badge HTML com 3 estados

```html
{% if freshness.generated_at %}
  {% if not freshness.is_stale and freshness.source == "fresh" %}
    <span class="badge badge-ok">Frescos · {{ freshness.generated_at[:10] }}</span>
  {% else %}
    <span class="badge badge-warn">Cache · última consulta: {{ freshness.generated_at[:10] }}</span>
  {% endif %}
{% else %}
  <span class="badge badge-stale">Sem dados de comparação</span>
{% endif %}
```

### Anti-Patterns a Evitar

- **Bloquear o upload quando tiagofelicia.pt está em baixo:** A resposta HTTP do upload deve ser sempre imediata. O background task falha silenciosamente — o utilizador vê confirmação do upload e badge "cache" na próxima visita. Nunca mostrar erro 500 por indisponibilidade de site externo.
- **Nova migration sem necessidade:** Se a abordagem "actualizar cached_at" funciona, não adicionar coluna `fetch_status` — menos complexidade de schema.
- **Threshold hardcoded no template:** O threshold `FRESH_THRESHOLD_HOURS` deve ser constante Python em `data_loader.py`, não lógica no template Jinja2.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Upsert SQLite | SQL manual com SELECT + INSERT/UPDATE | `sqlite_insert().on_conflict_do_update()` | já importado em upload.py, atómico, idempotente |
| Detecção de disponibilidade de site externo | ping/curl antes de consultar | try/except à volta de `analyse_with_tiago()` | já existe — não acrescentar lógica de probe |
| Persistência de estado "site em baixo" | ficheiro de lock ou flag em memória | `cached_at` timestamp na BD | já existe, persistente entre restarts do container |

---

## Common Pitfalls

### Pitfall 1: `on_conflict_do_nothing` impede actualização de `cached_at`

**O que vai correr mal:** Com o código actual (Phase 7), se a consulta a tiagofelicia.pt ter sucesso para um mês que já existe na BD, o `ON CONFLICT DO NOTHING` ignora o insert — `cached_at` fica com a data original. O badge vai sempre mostrar dados antigos mesmo que a consulta tenha sido bem-sucedida.

**Como evitar:** Mudar para `on_conflict_do_update` que actualiza `cached_at` (e os dados) quando há sucesso.

**Warning signs:** `cached_at` em BD nunca muda após o primeiro insert.

### Pitfall 2: `cached_at` armazenado como string vs datetime

**O que vai correr mal:** `get_freshness_from_sqlite` já trata ambos os casos (tem `isinstance(max_cached_at, str)` check). Manter essa robustez ao actualizar.

**Como evitar:** Sempre gravar `cached_at` como `datetime` object (SQLAlchemy converte para ISO string no SQLite).

### Pitfall 3: Badge duplicado

**O que vai correr mal:** `frescura_badge.html` é incluído em `dashboard.html` (na header) E também poderia aparecer em `dashboard_content.html` (via HTMX swap). Ao trocar de local via selector, o badge na header não actualiza porque só o `#dashboard-content` é swapped.

**Como evitar:** Mover o badge para dentro de `dashboard_content.html` para que actualize com o HTMX swap, OU usar HTMX `hx-swap-oob` para actualizar o badge fora do target. A solução mais simples: mover o badge para `dashboard_content.html` e remover da header.

**Warning signs:** Mudar de local no selector e o badge continuar a mostrar a frescura do local anterior.

### Pitfall 4: Testes existentes com `is_stale` hardcoded

**O que vai correr mal:** `test_web_data_loader.py` e outros testes podem verificar o dict `freshness` sem campo `source`. Ao adicionar `source` ao dict, os testes existentes continuam a passar (não quebram por adição de chave nova), mas os novos testes para Phase 10 devem verificar explicitamente `source`.

**Como evitar:** Verificar que os testes existentes não fazem `assert freshness == {...}` com dict exacto. Uma leitura rápida mostra que não fazem — usam acesso por chave.

### Pitfall 5: `FRESH_THRESHOLD_HOURS` vs `STALE_THRESHOLD_DAYS`

**O que vai correr mal:** Já existe `STALE_THRESHOLD_DAYS = 40` em `get_freshness_from_sqlite`. Um threshold separado para "fresh" (ex: 48h) pode conflituar com a lógica `is_stale`.

**Como evitar:** Usar um único threshold ou tornar os dois thresholds independentes e claramente nomeados. `is_stale` mantém-se para "dados muito antigos (>40 dias)"; `source = "cache"` aplica-se quando `cached_at > FRESH_THRESHOLD_HOURS` mas < 40 dias.

---

## Code Examples

### Upsert com actualização de cached_at (fonte: SQLAlchemy docs + código existente em upload.py)

```python
# Fonte: padrão já em uso em upload.py (Phase 7) — adaptar do_nothing → do_update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from src.db.schema import comparacoes
from datetime import datetime, timezone

stmt = sqlite_insert(comparacoes).values(
    location_id=location_id,
    year_month=row.year_month,
    top_3_json=json.dumps(result.get("top_3", []), ensure_ascii=False),
    current_supplier_result_json=json.dumps(
        result.get("current_supplier_result"), ensure_ascii=False
    ),
    generated_at=result.get("generated_at", ""),
    cached_at=datetime.now(timezone.utc),
).on_conflict_do_update(
    index_elements=["location_id", "year_month"],
    set_={
        "top_3_json": sqlite_insert(comparacoes).excluded.top_3_json,
        "current_supplier_result_json": sqlite_insert(comparacoes).excluded.current_supplier_result_json,
        "generated_at": sqlite_insert(comparacoes).excluded.generated_at,
        "cached_at": datetime.now(timezone.utc),
    }
)
with engine.begin() as conn:
    conn.execute(stmt)
```

### Cálculo de `source` em get_freshness_from_sqlite

```python
# Em data_loader.py — acrescentar ao dict retornado
FRESH_THRESHOLD_HOURS = 48

hours_ago = delta.total_seconds() / 3600
source = "fresh" if hours_ago <= FRESH_THRESHOLD_HOURS else "cache"

return {
    "days_ago": days_ago,
    "is_stale": days_ago > STALE_THRESHOLD_DAYS,
    "generated_at": cached_at.isoformat(),
    "source": source,  # novo campo
}
# Também adicionar "source": "none" ao dict de fallback (sem dados)
```

### Badge com 3 estados (frescura_badge.html)

```html
{% if freshness.generated_at %}
  {% if freshness.source == "fresh" %}
    <span class="badge badge-ok">
      Comparação fresca · {{ freshness.generated_at[:10] }}
    </span>
  {% else %}
    <span class="badge badge-warn">
      Cache · última consulta: {{ freshness.generated_at[:10] }}
      {% if freshness.days_ago is not none %} (há {{ freshness.days_ago }} dias){% endif %}
    </span>
  {% endif %}
{% else %}
  <span class="badge badge-stale">Sem dados de comparação</span>
{% endif %}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `on_conflict_do_nothing` (Phase 7) | `on_conflict_do_update` com cached_at | Phase 10 | cached_at actualiza em cada consulta bem-sucedida |
| Badge binário (stale/ok) | Badge ternário (fresh/cache/sem dados) | Phase 10 | utilizador sabe se dados são em tempo real ou antigos |

---

## Runtime State Inventory

> Não é fase de rename/refactor — esta secção aplica-se de forma simplificada.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Tabela `comparacoes` em SQLite com `cached_at` — rows existentes têm timestamps históricos | Nenhuma migration necessária se usar abordagem "actualizar cached_at"; rows antigas terão `source = "cache"` até próxima consulta bem-sucedida |
| Live service config | Nenhum | — |
| OS-registered state | Nenhum | — |
| Secrets/env vars | Nenhum | — |
| Build artifacts | Nenhum | — |

---

## Environment Availability

> Step 2.6: Dependências externas desta fase.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| SQLite (via SQLAlchemy) | Cache fallback | ✓ | já em uso | — |
| Python pytest | Testes | ✓ | instalado | — |
| tiagofelicia.pt | Consulta fresca | ✗ (externo, pode estar em baixo) | — | Cache SQLite — é precisamente o que esta fase implementa |

**Missing dependencies com no fallback:** Nenhum — o fallback para o site externo é o objectivo desta fase.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pytest.ini (raiz do projecto) |
| Quick run command | `python -m pytest tests/test_web_dashboard.py tests/test_web_data_loader.py -q` |
| Full suite command | `python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COMP-03 | Dashboard continua a mostrar ranking com tiagofelicia.pt inacessível | unit | `python -m pytest tests/test_web_dashboard.py -q -k "cache"` | ❌ Wave 0 |
| COMP-03 | `get_freshness_from_sqlite` retorna `source="cache"` quando cached_at antigo | unit | `python -m pytest tests/test_web_data_loader.py -q -k "source"` | ❌ Wave 0 |
| COMP-04 | Badge mostra "Comparação fresca" quando source=fresh | unit | `python -m pytest tests/test_web_dashboard.py -q -k "badge_fresh"` | ❌ Wave 0 |
| COMP-04 | Badge mostra "Cache" quando source=cache | unit | `python -m pytest tests/test_web_dashboard.py -q -k "badge_cache"` | ❌ Wave 0 |
| COMP-04 | Badge mostra "Sem dados" quando sem comparações | unit (já parcial) | `python -m pytest tests/test_web_dashboard.py -q` | ✅ indirectamente |

### Sampling Rate

- **Por task:** `python -m pytest tests/test_web_dashboard.py tests/test_web_data_loader.py -q`
- **Por wave:** `python -m pytest tests/ -q`
- **Phase gate:** Suite completa verde antes de `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_web_dashboard.py` — acrescentar testes `badge_fresh`, `badge_cache`, `cache_fallback_shows_ranking`
- [ ] `tests/test_web_data_loader.py` — acrescentar testes `freshness_source_fresh`, `freshness_source_cache`
- [ ] Não é necessário criar novos ficheiros — acrescentar ao existente

---

## Open Questions

1. **Posição do badge no layout**
   - O que sabemos: badge está em `dashboard.html` na header (fora do HTMX swap zone)
   - O que é incerto: ao mudar de local via selector HTMX, o badge da header não actualiza
   - Recomendação: mover badge para `dashboard_content.html` para que actualize com o swap. Verificar se o design atual da header ainda faz sentido sem o badge.

2. **`on_conflict_do_update` — referência a `.excluded`**
   - O que sabemos: `sqlite_insert().excluded` dá acesso aos valores novos do insert
   - O que é incerto: sintaxe exacta para o `set_` dict no SQLAlchemy Core (não ORM)
   - Recomendação: usar `set_={"cached_at": datetime.now(timezone.utc)}` com valor literal, não `.excluded`, para evitar ambiguidade. Verificar com teste.

---

## Sources

### Primary (HIGH confidence)

- Código do projecto lido directamente — `src/web/routes/upload.py`, `src/web/services/data_loader.py`, `src/db/schema.py`, `src/web/templates/partials/frescura_badge.html`
- `tests/conftest.py` e `tests/test_web_dashboard.py` — 29 testes a passar, baseline verificado

### Secondary (MEDIUM confidence)

- SQLAlchemy SQLite upsert pattern: `on_conflict_do_update` com `index_elements` — padrão documentado, já em uso no projecto (upload.py usa `on_conflict_do_nothing` do mesmo dialect)

### Tertiary (LOW confidence)

- Nenhum

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — sem dependências novas, tudo já instalado
- Architecture: HIGH — código existente lido e compreendido, padrão de upsert já em uso
- Pitfalls: HIGH — identificados por leitura directa do código (badge fora do HTMX zone, cached_at nunca actualiza)

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (dependências estáveis — sem risco de obsolescência)
