# RAW COMPLETE v1 — безопасный план реализации после red-team revision

Статус: **REVISED — NOT OWNER APPROVED**. Этот документ не создаёт Google Sheets и не разрешает ETL/production changes.

## Фазы

| Phase | Вход | Действие | Результат | Blocking check | Rollback/stop |
|---|---|---|---|---|---|
| 0 — independent re-audit | Revised 8-document contract + Revision Report | Проверить 32 sheets, 466 fields, 38 mappings, 171 validations и hashes | Независимый verdict | 0 critical contract defects | Stop; документы возвращаются на revision |
| A — empty target | Owner-approved post-audit contract; Drive access | Создать отдельный файл `RUKODELIE AI Product Knowledge — Пряжа RAW COMPLETE v1` | Пустой isolated workbook | File ID отличается от CURRENT RAW; projected capacity ≤3,5m | Удалить только новый пустой файл |
| B — schema | Approved dictionary/mapping checksums | Создать ровно 32 sheets и 466 text-safe headers, без excess rows | Schema-only workbook | Exact sheet/header checksum; 0 unknown fields | Пересоздать только новый файл |
| C — Phase 1 test | Schema-only target; read-only 1C | Выгрузить 3 товара и все варианты: Puffy/photo, no-photo, zero-stock; включить prices, HTML, filters, leading-zero codes | Test dataset + run accounting | PK/FK/orphan/source duplicate/owner type/HTML/zero-stock/exact-photo checks | Очистить новый test target; CURRENT RAW не трогать |
| D — snapshot validation | Успешный Phase 1 test | Проверить current price selection и current stock aggregation на одном cutoff; повторить тот же run | Signed quality evidence | Stable checksum; idempotent reload; stock total reconciliation; explicit zeros | Reject current snapshot partitions |
| E1 — Phase 1 full | Owner accepts test report | Загрузить все REQUIRED sources для 204/9 114 | Complete required core | 204 products; 9 114 variants; PHASE 1 blockers closed; projected cells ≤3,5m | Reject/replace only failed new-workbook partition |
| E2 — Phase 2 | Phase 1 frozen; Phase 2 blockers closed | Загрузить JUSTIFIED_OPTIONAL sources малыми batches | Extended contract scope | Ozon complete traversal; optional misses reported | Reject affected optional partition; Phase 1 remains valid |
| F — full validation | Complete selected phases | Выполнить 171 validations и quality report | Blocking/warning report | 0 BLOCKING failures; WARNING explicitly accepted/reported | Не freeze при blocking failure |
| G — freeze v1 | Owner accepts quality report | Защитить headers/source sheets, записать schema/run checksums | Immutable frozen export | Same-cutoff rerun stable; access reviewed | Retain rejected copy isolated; no consumers |
| H — IDEAL design | Frozen RAW COMPLETE v1 | Отдельная задача на PRODUCT/VARIANT IDEAL | Новый независимый contract | RAW values не перезаписываются | Discard IDEAL draft only |

Optional означает «не блокирует Phase 1», а не «не требуется». Все 32 headers могут быть созданы на Phase B; data load выполняется очередями.

## Порядок каждого extraction run

1. Создать `RAW_EXTRACTION_RUNS` со статусом `STARTED`.
2. Зафиксировать schema version, exact EntitySet/source role, masked scope, selected fields, cutoff и extractor version.
3. Выполнять только read-only GET малыми batches.
4. Сохранить source-close staging вне production.
5. Выполнить schema/type/PK/source-duplicate/FK/orphan/null-profile checks.
6. Для prices выбрать latest source record на cutoff; для stock вычислить signed balance, input count и canonical input checksum.
7. Сформировать полный replacement partition в staging и сверить checksum/counts.
8. Атомарно заменить только validated current partition; не append daily price/stock rows.
9. Зафиксировать `expected`, `extracted`, `validated`, `rejected`, `missing_relation`, warnings и checksum.
10. Перевести run в `SUCCESS`, `PARTIAL`, `FAILED` или `REJECTED`.

## Current snapshot replacement

- `RAW_CURRENT_PRICES` и `RAW_CURRENT_STOCK` содержат один current/frozen cutoff.
- Новый полный snapshot сначала полностью валидируется вне target, затем заменяет текущий partition.
- Повтор того же run/cutoff не увеличивает row count и не меняет checksum.
- Предыдущий утверждённый snapshot при необходимости сохраняется отдельным frozen export, а не дополнительными строками в том же workbook.
- `RAW_EXTRACTION_RUNS` append-only, но это история запусков, не история каждой цены/остатка.
- Future analytical price/stock history находится вне RAW COMPLETE v1.
- Нулевые warehouse rows сохраняются; `stock_total` воспроизводится validation control и не заменяет warehouse detail.

## Google Sheets operating rules

1. До Phase A считать actual projected cells; stop/review при прогнозе >3,5 млн.
2. API values payload целится ≤2 MB; batches ограничиваются фактическим serialized size, не только rows.
3. Использовать batch operations, exponential backoff и bounded retries; request timeout не должен создавать duplicate load.
4. Не создавать default excess rows/columns; resize под actual used range.
5. Не использовать full-column, volatile или cross-million-row formulas; joins/checksums/validation выполняются вне Sheets.
6. HTML писать как raw text; до записи проверять максимум 50 000 characters/cell.
7. Не писать binary/Base64.
8. Не выполнять массовые interactive sorts/filters во время load.
9. Логировать duration, request count, retry count, payload bytes и final cells без secrets.

Официальный лимит 10 млн cells не является единственным критерием. Для 10 000 products / 100 000 variants требуется PostgreSQL или BigQuery; миграция не входит в эту задачу.

## Validation semantics

- `BLOCKING`: partition/run нельзя принять; применяется указанный rollback effect.
- `WARNING`: данные/partition сохраняются только если source fact не теряется; warning входит в quality report.
- `AUTOMATIC_FIRST_LOAD`: schema/type contract gate до первого полного load.
- `AUTOMATIC_EACH_LOAD`: повторяется на каждом snapshot.
- `MANUAL_REVIEW`: допускается только когда критерий действительно не автоматизируем; визуальные проверки не маскируются как automatic.

## Rollback и ограничения

- CURRENT RAW, AI Seller, order flow и production не участвуют в rollback.
- До freeze удаляется/пересоздаётся только новый workbook или его failed partition.
- После freeze correction создаёт новый schema version/frozen export; утверждённое evidence не переписывается.
- Никакого переключения AI Seller в этом плане нет.
- Перед будущим подтверждением заказа необходим live read-only price/stock check в 1С; сейчас он только зафиксирован как future requirement.
