---
status: partial
phase: 07-upload-xlsx-ingest-o-de-dados
source: [07-VERIFICATION.md]
started: 2026-03-30T17:35:00Z
updated: 2026-03-30T17:35:00Z
---

## Current Test

[aguarda verificação humana]

## Tests

### 1. Upload XLSX real via browser
expected: Formulário aparece no dashboard; após upload, confirmação mostra período importado (ex: "2024-01 a 2024-12") e local detectado por CPE
result: [pending]

### 2. Criar local via UI e verificar no selector
expected: Novo local aparece no selector do dashboard após criação; dados do local ficam persistidos em SQLite
result: [pending]

### 3. Idempotência de upload
expected: Segunda ingestão do mesmo XLSX reporta "0 meses inseridos" — sem duplicação de dados
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
