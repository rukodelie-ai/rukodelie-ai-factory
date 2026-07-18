# RAW COMPLETE v1 — безопасный план реализации

Реализация этим документом **не выполняется**. Каждая фаза требует завершения предыдущей.

| Phase | Вход | Действие | Результат | Проверка | Критерий остановки | Rollback |
|---|---|---|---|---|---|---|
| A — новая таблица | Owner-approved contract; Drive access | Create a separate Google Sheets file named RUKODELIE AI Product Knowledge — Пряжа RAW COMPLETE v1 | Empty isolated file with owner recorded | File ID differs from CURRENT RAW; no production references | Stop if target name/file scope ambiguous | Delete only newly created empty file; CURRENT RAW untouched |
| B — sheets/headers | Approved Data Dictionary checksum | Create exactly 34 sheets and text-safe headers; preformat IDs/codes as text | Schema-only workbook | Header checksum equals contract; no default excess rows | Stop on any missing/extra sheet or field | Delete newly created file and recreate; no data rollback required |
| C — limited test | Schema-only workbook; read-only 1C access | Extract 3 products including Puffy and all their variants; load source-close rows | Small test dataset + extraction runs | PK/FK/provenance/HTML/leading zeros verified | Stop on secret exposure, orphan core FK, duplicate PK, or source mutation risk | Clear only new test workbook and preserve run/error logs externally |
| D — relation validation | Validated test load | Validate product→variant→photo→scheme→file→binary metadata and commercial snapshots | Signed validation report | All mandatory FK checks pass; missing optional relations counted | Stop if exact photo relation can map to another variant or stock totals mismatch | Discard test workbook; no CURRENT RAW or production change |
| E — full 204 load | Owner approval of test report | Run small-batch read-only extraction for 204 products and load all 34 sheets | Complete scoped RAW | Control counts reconciled as expected/extracted/validated/rejected/missing | Stop on partial core product/variant counts, repeated auth errors, or >7m projected cells | Discard new RAW COMPLETE file or replace failed run partition only |
| F — checksums/quality | Complete full load | Run validation matrix; calculate row/canonical checksums and quality report | Quality evidence attached to extraction run | 204 products and 9,114 variants exact; no blocking errors | Stop if any P0/P1 validation fails | Keep failed file isolated; do not freeze or connect consumers |
| G — freeze v1 | Owner accepts quality report | Set schema status FROZEN; protect headers and source sheets; record file checksum/counts | Immutable RAW COMPLETE v1 snapshot | Re-run gives stable checksums at same cutoff; access reviewed | Stop if any consumer is already pointed to draft file | Revoke draft access or retain as rejected audit copy |
| H — IDEAL design | Frozen RAW COMPLETE v1 | Start a separate architecture task for PRODUCT/VARIANT IDEAL | New approved IDEAL contract | No edits to frozen RAW; AI-generated fields isolated | Stop if IDEAL proposes overwriting RAW values | Discard IDEAL draft only |

## Порядок внутри каждого extraction run

1. Создать RAW_EXTRACTION_RUNS со статусом STARTED.
2. Прочитать source metadata/version without secrets.
3. Извлекать только read-only GET малыми batches, исключая IIS 404.15.
4. Сохранить staging вне production.
5. Выполнить schema/type/PK/FK validation.
6. Загрузить run partition идемпотентным upsert.
7. Вычислить canonical checksum.
8. Зафиксировать expected/extracted/validated/rejected/missing_relation.
9. Перевести статус в SUCCESS, PARTIAL или FAILED.

## Правила rollback

- CURRENT RAW, AI Seller и production никогда не участвуют в rollback RAW COMPLETE.
- До freeze безопаснее удалить/пересоздать только новую отдельную таблицу.
- После freeze исправление создаёт новый schema_version/run; frozen evidence не переписывается.
- Никакой фазы переключения AI Seller в этом плане нет.
