# Feature Landscape

**Domain:** Personal electricity monitoring + supplier comparison (Portugal, E-REDES)
**Milestone scope:** Multi-location support + web dashboard (on top of existing backend pipeline)
**Researched:** 2026-03-28
**Confidence:** MEDIUM — domain knowledge + project context; WebSearch unavailable; Portuguese market specifics from training data (Aug 2025 cutoff)

---

## Context: What Already Exists

The backend pipeline is implemented (not yet end-to-end validated). The dashboard is net-new.

| Already built | Not built |
|---------------|-----------|
| E-REDES download + normalisation | Multi-location config/state |
| Local catalogue comparison engine | Multi-CPE download selection |
| tiagofelicia.pt scraping comparison | Web dashboard |
| Monthly Markdown report generation | requirements.txt |
| macOS launchd scheduler + watcher | End-to-end validation |

The dashboard **reads outputs the pipeline already produces** — it does not replace or duplicate pipeline logic.

---

## Table Stakes

Features that must exist for the tool to be useful. Without these, opening the dashboard is pointless.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Monthly consumption history chart | Core reason to open the tool; spot trends, seasonal patterns | Low | Chart.js bar chart; vazio/fora_vazio stacked |
| Current supplier ranking table | The tool's primary output — "who is cheapest today" | Low | Already produced by pipeline as JSON; just render |
| Savings recommendation (current vs best) | Answers the core question: "compensa mudar?" | Low | Pipeline already calculates; display delta in euros/year |
| Per-location view (switch between CPEs) | Tool manages two locations; without this it's one-location | Low | URL param or tab; data already segregated by CPE |
| Last updated / data freshness indicator | User needs to know if data is current or stale | Low | Display date of most recent CSV processed |
| Bi-horário vs mono-horário split | E-REDES data has vazio/fora_vazio; hiding this loses information | Low | Show both periods in consumption and cost breakdown |
| Mobile-readable layout | Dashboard will be checked occasionally from phone | Low | HTMX + simple CSS grid; not a full mobile app |

**Complexity note:** All table stakes are Low because the pipeline already produces the underlying data. The dashboard renders it — it does not compute it.

---

## Differentiators

Features not universally present in personal energy tools, but genuinely valuable for this specific use case.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Side-by-side location comparison | Two properties, same account — spot if one is anomalous vs the other | Medium | Requires multi-location milestone to be complete first; normalise by kWh/day for fair comparison |
| Year-over-year monthly delta | Did July 2025 cost more than July 2024? Surfaces seasonal creep | Low | Computed from existing CSV history; display as % change badge |
| "Best tariff trajectory" chart | Show over time which supplier would have been cheapest — not just today | Medium | Requires replaying catalogue history; only possible if tariff snapshots are persisted |
| Savings accumulation since switch | If user acted on a recommendation, track cumulative saving | Medium | Requires recording which supplier is active per location + date; manual input |
| tiagofelicia.pt vs local catalogue diff | When results diverge, surface it — signals price catalogue staleness | Low | Already have both results; show agreement/disagreement badge |
| Recommendation confidence indicator | Flag when recommendation is marginal (e.g. only 3% cheaper — not worth switching) | Low | Threshold configurable; simple logic on delta percentage |
| Export month report as PDF | Useful for documenting decisions over time | Medium | WeasyPrint or wkhtmltopdf; or just print-to-PDF from browser |

**Recommendation on differentiators to build first:** Year-over-year delta (Low complexity, high insight) and tiagofelicia.pt vs local diff badge (Low complexity, directly validates pipeline reliability). Defer "best tariff trajectory" and savings accumulation — they require data persistence work beyond the current scope.

---

## Anti-Features

Tempting to build, but not worth it for a personal tool with two locations and monthly granularity.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Real-time or daily consumption graphs | E-REDES only provides data monthly via XLSX download; real-time requires Shelly hardware + always-on integration; PROJECT.md already deferred this | Aggregate monthly is sufficient for tariff decisions |
| User accounts / authentication | Single-user personal tool on localhost; adding login adds complexity with zero security benefit | Run dashboard on localhost only; if exposed, use macOS firewall or SSH tunnel |
| Supplier auto-switching workflow | Contractual risk; requires integration with supplier APIs that don't exist publicly in Portugal | Show recommendation clearly; user acts manually |
| Budget alerts / push notifications | macOS osascript notifications already handle the monthly trigger; web push adds a service worker, VAPID keys, and ongoing maintenance | Keep alerts in the existing launchd + osascript layer |
| Consumption forecasting / ML | Two locations, monthly data, < 24 data points per location per year — sample too small for meaningful models | Simple 12-month rolling average is sufficient context |
| Appliance-level breakdown | Requires smart plugs per circuit or Shelly clamps; out of scope per PROJECT.md | Aggregate per location is the right granularity |
| Dark mode toggle | HTMX + Jinja personal tool; prefers-color-scheme CSS media query is sufficient | Use CSS `@media (prefers-color-scheme: dark)` — no JS toggle needed |
| Internationalisation (i18n) | Single-user, Portuguese, single locale; i18n adds template complexity for zero benefit | Hardcode PT-PT throughout |
| Admin panel to edit tariff catalogue | Catalogue is a JSON file; editing in a text editor is simpler and less error-prone than a web form | Document JSON structure clearly; validate on load |

---

## Feature Dependencies

```
Multi-location config (backend)
  └── Per-location view (dashboard)
        └── Side-by-side location comparison

Monthly CSV history (existing pipeline)
  └── Monthly consumption history chart
        └── Year-over-year monthly delta

Pipeline JSON output (existing)
  └── Current supplier ranking table
        └── tiagofelicia.pt vs local catalogue diff badge
              └── Recommendation confidence indicator
                    └── Savings recommendation display

[Future — requires new data persistence]
  Savings accumulation since switch  (needs: active supplier log)
  Best tariff trajectory chart       (needs: historical tariff snapshots)
```

---

## MVP Recommendation for Dashboard Milestone

**Build in this order:**

1. **Per-location view with tab/selector** — prerequisite for everything else; unblocks multi-location milestone
2. **Monthly consumption history chart** (stacked bar: vazio / fora de vazio, Chart.js) — core visual
3. **Supplier ranking table** (read from existing pipeline JSON output) — primary decision output
4. **Savings recommendation display** — delta euros/year, current vs best, with confidence threshold badge
5. **Last updated indicator** — data freshness, single line, essential for trust
6. **Year-over-year monthly delta badge** — Low complexity, high informational value, no new data needed
7. **tiagofelicia.pt vs local catalogue diff indicator** — validates pipeline reliability, Low complexity

**Defer to v2:**
- Side-by-side location comparison (after multi-location is validated end-to-end)
- Savings accumulation since switch (requires manual active-supplier input)
- Best tariff trajectory chart (requires tariff snapshot persistence)
- PDF export (nice-to-have, adds dependency)

---

## Personal Tool vs Enterprise Tool Distinctions

| Concern | Enterprise Tool | This Tool |
|---------|----------------|-----------|
| Auth | Required | Not needed (localhost) |
| Multi-user | Core feature | Single user, irrelevant |
| API rate limits / billing | Must handle | N/A |
| Data retention policy | Legal requirement | Keep everything, forever |
| Audit log | Required | Not needed |
| Accessibility (WCAG) | Required | Best effort, not a blocker |
| Mobile app | Often required | Responsive web is sufficient |
| Uptime SLA | Required | Run on demand is fine |
| Observability / logging | Required | Print to stdout / macOS log |

The tool should be built to the personal tool standard. Any feature that makes sense only at the enterprise level is an anti-feature here.

---

## Portuguese Market Specifics (Confidence: MEDIUM)

These affect feature design, not just labelling:

- **Bi-horário tariff structure** is the norm for E-REDES residential. Vazio (off-peak) and fora de vazio (peak) hours are legally defined by ERSE. Both periods must be surfaced in consumption and cost display.
- **Tariff change seasonality**: ERSE adjusts regulated tariffs annually (typically January). The tool should make it easy to spot when the catalogue was last updated — a staleness warning if catalogue JSON is > 90 days old is reasonable.
- **Switching friction**: Changing supplier in Portugal takes ~20 days and requires a new contract. The recommendation threshold (e.g. "only recommend switching if saving > 5% annually") should reflect this friction.
- **tiagofelicia.pt dependency**: This is the ERSE-aligned official simulator. It is the authoritative source but is a scraping dependency. The local catalogue is the fallback. The dashboard should surface which source produced the ranking.

---

## Sources

- Project context: `.planning/PROJECT.md`, `MVP.md` (HIGH confidence — primary source)
- Domain knowledge: Home Assistant Energy Dashboard patterns, Portuguese ERSE tariff structure, tiagofelicia.pt simulator (MEDIUM confidence — training data, Aug 2025 cutoff)
- Web research: Not available (WebSearch and Bash tools restricted in this session)
- Note: No web verification was possible. Portuguese market specifics (ERSE rules, switching timeline) should be validated against current ERSE documentation before implementation decisions are made.
