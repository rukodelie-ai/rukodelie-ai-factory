# RAW COMPLETE v1 — decision report

Статус: **REVISED — NOT OWNER APPROVED**  
Дата ревизии: **2026-07-18**  
Исходный независимый verdict: **C. REVISE BEFORE APPROVAL**.

Этот документ фиксирует исправление контракта. Он не утверждает архитектуру, не разрешает создание Google Sheets/ETL и не меняет CURRENT RAW, production или AI Seller.

## REVISION AFTER RED-TEAM AUDIT

### 1. Решение

- Сохранить отдельный source-close RAW COMPLETE v1; CURRENT RAW остаётся неизменяемым.
- Активная физическая схема: **32 листа, 466 полей, 38 EntitySet mappings, 171 validation**.
- Очередность: **19 REQUIRED / PHASE 1** и **13 JUSTIFIED_OPTIONAL / PHASE 2**; optional не блокирует первую предметную загрузку.
- Цена и остаток представлены одним current/frozen snapshot без daily append.
- Binary/Base64, AI/IDEAL fields и неподтверждённые physical source fields отсутствуют.
- AI Seller direct usage для RAW COMPLETE: **NO**.

### 2. Четыре критические проблемы

| ID | Исходная проблема | Статус | Принятое решение | Изменённые документы | Проверка | Остаточный риск |
|---|---|---|---|---|---|---|
| C1 | Невалидные однопольные PK metadata-листов делали gate неизбежно падающим | RESOLVED | PK `RAW_DATA_DICTIONARY=(sheet_name,field_name)`; PK `RAW_ENTITYSET_MAPPING=(target_sheet,source_entityset,source_role)` | Dictionary, Mapping, Architecture, Import Plan, Validation Matrix | 466 и 36 уникальных composite keys; duplicate count 0 | Только риск ручного изменения headers; блокируется schema checksum |
| C2 | Остатки смешивали RAW и STAGING; aggregate rows имели ложный `source_record_id`; total дублировался | RESOLVED | `RAW_CURRENT_STOCK` — current aggregate snapshot с cutoff, rule, input count/checksum; `RAW_STOCK_TOTALS` удалён; `stock_total` — validation output | Все 8 документов | Removed sheets absent; lineage check использует input-set evidence; zero rows/warehouse grain сохранены | Формула агрегации и cutoff должны быть доказаны Phase 1 test extraction |
| C3 | FK/type rules допускали false links и orphan | RESOLVED | Namespaced classification/listing keys; raw polymorphic owner/package IDs сохранены; typed FK только по exact type/membership; binary pair key; product-level price FK nullable | Dictionary, Mapping, ER, Import Plan, Validation Matrix, Open Questions, Architecture | Все FK target fields существуют, являются keys и type-compatible; 0 ссылок на удалённые sheets | Package role и external optional coverage проверяются отдельными classified tests |
| C4 | Validation Matrix содержала 6 impossible blocking checks и не имела исполнимой gate-семантики | RESOLVED | 11 обязательных колонок; impossible checks исправлены/удалены; severity и execution mode явные; 168 BLOCKING + 3 WARNING | Validation Matrix, Import Plan, Architecture, Open Questions | 171 unique IDs; 0 missing targets; required criteria nonblank; impossible IDs/evidence отсутствуют | Фактический pass доказывается только на test/full extraction, не этой document revision |

### 3. Десять minor issues

| № | Замечание аудита | Статус после revision | Решение/evidence |
|---:|---|---|---|
| 1 | 14 physical `UNCONFIRMED_SOURCE` fields | RESOLVED | 12 удалены; 2 `language_code` объявлены `TECHNICAL_REQUIRED=CONSTANT(und)`; physical unconfirmed count 0 |
| 2 | Пустой speculative `RAW_PACKAGE_ITEMS` | RESOLVED | Исключён из physical v1; raw `Упаковка_Key` сохранён без выдуманного FK |
| 3 | 7 duplicate derived fields | RESOLVED | MIME/hash/order централизованы; source LineNumber сохранён |
| 4 | Неподтверждённый variant `is_primary_derived` | RESOLVED | Поле удалено; exact variant file link не подменяется primary inference |
| 5 | 29 multi-source/expression fields нельзя было проверить по одной property | RESOLVED | `ROW_SOURCE_ENTITYSET` + exact `source_role` выбирают branch-specific property; статус `CONFIRMED_BY_SOURCE_ROLE` |
| 6 | 38 contract-required fields строже OData nullable metadata | RESOLVED AS GATE; EVIDENCE PENDING | Добавлен `CTRL-REQUIRED-NULL-PROFILE`; test extraction является `PHASE_1_BLOCKER`; fabricated defaults запрещены |
| 7 | Blanket deletion rule на 476 fields | RESOLVED | Source DeletionMark, current replacement, technical recompute и retention разделены по semantics |
| 8 | Неверный расчёт cells | RESOLVED | Пересчёт по 32 sheet capacities и 466 fields: 3 381 673 cells |
| 9 | Pending Ozon/variant files/palettes/prices маскировались readiness-текстом | RESOLVED | Вопросы классифицированы с exact test package и success criterion; статус NOT OWNER APPROVED |
| 10 | Stop at 7m был поздним; не было API operating contract | RESOLVED | Stop/review >3.5m, payload target ≤2 MB, batch/backoff/timeout, actual used range, запрет workbook-wide formulas |

### 4. Контрольные изменения

| Показатель | До revision | После revision |
|---|---:|---:|
| Physical sheets | 34 | 32 |
| Fields | 514 | 466 |
| EntitySet mappings | 38 | 38, включая 2 control-only lineage mappings для исключённых/объединённых sheets |
| Validations | 169 | 171 |
| Physical fields without confirmed/technical origin | 14 | 0 |
| Cells | 3 452 888 заявлено; red-team as-is correction ≈3 454 844 | 3 381 673 upper envelope |
| PREMATURE sheets | 2 | 0 active |
| DUPLICATIVE sheets | 1 | 0 active |

Validation distribution after revision: **168 BLOCKING**, **3 WARNING**; **155 AUTOMATIC_EACH_LOAD**, **16 AUTOMATIC_FIRST_LOAD**, **0 MANUAL_REVIEW**.

### 5. Модель current prices/current stock

- `RAW_CURRENT_PRICES`: одна выбранная source-close запись на product + `variant_id_raw` + price type при едином cutoff. Zero GUID остаётся raw; typed variant FK nullable.
- `RAW_CURRENT_STOCK`: одна агрегированная строка на product + variant + warehouse при едином cutoff. Сохраняются все восемь virtual warehouses и explicit zero rows.
- Новый validated snapshot атомарно заменяет предыдущий; daily history в workbook не накапливается.
- `RAW_EXTRACTION_RUNS` хранит историю запусков, не историю каждой цены/остатка.
- Previous approved state допускается только как отдельный frozen export.
- Future live read-only price/stock check перед подтверждением заказа обязателен как отдельный этап, но сейчас не реализован.

### 6. Оставшиеся blockers

Контрактных critical defects, известных после этой correction, — **0**. Открыты **5 readiness/execution blockers**:

1. `BLOCKER`: независимый повторный red-team pass и owner decision.
2. `PHASE_1_BLOCKER`: exact count/closure variant attached files.
3. `PHASE_1_BLOCKER`: exact current-price count/reconciliation at one cutoff.
4. `PHASE_1_BLOCKER`: required-null profile and explicit policy.
5. `PHASE_2_BLOCKER`: complete Ozon mapping traversal/count.

Они не разрешают объявить контракт утверждённым. Подробные test packages и success criteria находятся в Open Questions.

### 7. Capacity decision

- Официальный Google Sheets limit: **10 000 000 cells**.
- Рабочий ориентир регулярно обновляемого проекта: **2–3 млн used cells**.
- Исправленный upper envelope: **3 381 673 cells**.
- До full load обязателен stop/review при projected **>3.5 млн cells**, превышении 50 000 characters/cell или невозможности выполнить refresh SLA.
- Для 10 000 products / 100 000 variants следующим storage tier должен быть PostgreSQL или BigQuery; migration не входит в v1.

## Рекомендация

Следующий и единственный разрешённый шаг: **повторный независимый red-team аудит восьми revised документов и Revision Report**. До его успешного verdict не создавать Google Sheets, не писать ETL и не переключать AI Seller.

## Финальное состояние решения

**READY FOR INDEPENDENT RE-AUDIT — NOT APPROVED FOR IMPLEMENTATION.**
