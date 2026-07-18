# RAW COMPLETE v1 — Revision Report

Дата: **2026-07-18**  
Основание: `RAW_COMPLETE_V1_RED_TEAM_AUDIT.md`  
Исходный verdict: **C. REVISE BEFORE APPROVAL**  
Статус результата: **REVISED — NOT OWNER APPROVED**

## 1. Executive summary

Исправлены все четыре критических класса дефектов и адресованы все десять minor issues red-team аудита без перепроектирования архитектуры. Физическая схема сокращена с 34 до **32 листов**, Data Dictionary — с 514 до **466 полей**. Сохранено **38 mappings**: два mapping исключённых/объединённых sheets переведены в control-only lineage, не создавая физических таблиц. Validation Matrix содержит **171 исполнимую проверку**. Физических полей `UNCONFIRMED_SOURCE` — **0**.

Цена и остаток закреплены как один current/frozen snapshot с атомарной заменой. Daily history, Base64, binary payload, IDEAL/AI fields, speculative package rows и дублирующий stock-total sheet отсутствуют. Расчётный upper envelope Google Sheets — **3 381 673 cells**; stop/review — до превышения **3,5 млн**.

Этот revision не утверждает контракт и не разрешает реализацию. Остаются **5 readiness/execution blockers**: независимый re-audit/owner decision, variant-file closure, current-price count, required-null profile и полный Ozon mapping.

## 2. Все замечания red-team аудита

| ID | Severity | Замечание | Статус | Исправление |
|---|---|---|---|---|
| C1 | CRITICAL | Metadata-листы имели невалидные однопольные PK | RESOLVED | Введены composite PK `(sheet_name,field_name)` и `(target_sheet,source_entityset,source_role)`; validations используют те же keys |
| C2 | CRITICAL | `RAW_STOCK_BALANCES` смешивал RAW/STAGING и имел false provenance; `RAW_STOCK_TOTALS` дублировал aggregate | RESOLVED | `RAW_CURRENT_STOCK` хранит current aggregate с cutoff/input count/checksum; total — validation output; физический total sheet удалён |
| C3 | CRITICAL | FK/type rules создавали false links/orphans | RESOLVED | Namespaced/typed/conditional keys, raw polymorphic values, nullable product-level price FK, binary composite key, external target identity |
| C4 | CRITICAL | 6 blocking validations были невыполнимы | RESOLVED | Impossible checks исправлены/удалены; evidence fields и gate semantics приведены к реальной схеме |
| M1 | MINOR | 14 physical fields без подтверждённого source | RESOLVED | 12 удалены, 2 language fields — deterministic technical `und` |
| M2 | MINOR | `RAW_PACKAGE_ITEMS` был speculative 0-row placeholder | RESOLVED | Physical sheet исключён; raw package keys сохранены; mapping остался control-only test lineage |
| M3 | MINOR | 7 derived fields дублировали source/canonical metadata | RESOLVED | Дубли MIME/hash/order удалены; canonical metadata централизована |
| M4 | MINOR | Variant `is_primary_derived` не имел правила | RESOLVED | Поле удалено; primary не выводится по неподтверждённой логике |
| M5 | MINOR | 29 multi-source/expression fields нельзя было field-level проверить | RESOLVED | `ROW_SOURCE_ENTITYSET`, exact `source_role` и branch-specific property expressions |
| M6 | MINOR | 38 required fields строже OData nullable metadata | RESOLVED AS CONTRACT GATE; EVIDENCE PENDING | `CTRL-REQUIRED-NULL-PROFILE`; fabricated defaults запрещены; execution остаётся PHASE_1_BLOCKER |
| M7 | MINOR | Blanket deletion rule механически применялся к 476 fields | RESOLVED | Source deletion, snapshot replacement и technical retention разделены |
| M8 | MINOR | Cells были посчитаны по неверным metadata row counts | RESOLVED | Полный per-sheet пересчёт по 32 sheets/466 fields/38 mappings |
| M9 | MINOR | Pending Ozon/files/palette/prices маскировались readiness-текстом | RESOLVED | Все вопросы классифицированы, имеют test package/success criterion; статус NOT OWNER APPROVED |
| M10 | MINOR | Stop at 7m был поздним; отсутствовал API operating contract | RESOLVED | Stop/review >3,5m, payload ≤2 MB, batch/backoff/timeout, actual used range, no workbook-wide formulas |

## 3. Исправления по критическим проблемам

### C1 — composite metadata keys

- `RAW_DATA_DICTIONARY`: ключ `sheet_name + field_name`; 466 уникальных combinations.
- `RAW_ENTITYSET_MAPPING`: ключ `target_sheet + source_entityset + source_role`; 38 уникальных combinations.
- Data Dictionary, Mapping, Architecture, Import Plan и Validation Matrix используют одинаковую key semantics.
- Остаточный риск: ручное изменение header/schema; блокируется first-load schema checksum.

### C2 — граница RAW/current snapshot для остатков

- `RAW_STOCK_BALANCES` переименован и переклассифицирован в `RAW_CURRENT_STOCK`.
- Aggregate row хранит `cutoff_at_utc`, `aggregation_rule`, `source_record_count`, `input_checksum_sha256`, `extraction_run_id`, а не одну вымышленную source record.
- Полная variant×warehouse matrix и explicit zero rows сохранены.
- `RAW_STOCK_TOTALS` исключён; `stock_total=SUM(quantity_available)` — воспроизводимый validation output.
- Original total mapping сохранён как control-only lineage к `RAW_CURRENT_STOCK`, не как physical sheet.

### C3 — FK, namespace и source typing

- Classifications используют namespaced `classification_id`; raw source category ID сохранён отдельно.
- Marketplace children формируют тот же platform-qualified `listing_id`, что parent; raw `Ref_Key` сохранён.
- Package references сохраняются как `package_id_raw` без FK до подтверждения типа.
- Variant owner сохраняется как `owner_raw`; typed product FK создаётся только при exact `owner_type_raw`.
- Product-level price сохраняет zero GUID в `variant_id_raw`; typed `variant_id` nullable.
- Product relation сохраняет внешний `target_product_source_id`; in-scope FK nullable.
- File→binary linkage использует `binary_storage_id` из exact pair `(file_id,file_type_raw)`; hash не является FK.
- Все объявленные FK разрешаются в существующие, type-compatible key fields.

### C4 — исполнимая Validation Matrix

- Новая schema matrix: `validation_id`, `target_sheet`, `rule`, `severity`, `execution_mode`, `required_input_fields`, `pass_criterion`, `failure_output`, `rollback_effect` плюс layer/check type.
- Исправлены оба metadata PK checks, current-stock lineage, no-substitution evidence и URL-security evidence.
- Source-row provenance удалена с aggregate total; отдельный physical total validation отсутствует.
- Итог: 171 unique validations; 168 BLOCKING, 3 WARNING; 155 EACH_LOAD, 16 FIRST_LOAD.

## 4. Изменённые документы

| Документ | Основные изменения |
|---|---|
| `RAW_COMPLETE_V1_ARCHITECTURE.md` | 32-sheet model, phase queues, current snapshots, capacity, Google Sheets operating conditions |
| `RAW_COMPLETE_V1_DATA_DICTIONARY.csv` | Composite PK, 466 confirmed/technical fields, corrected types/FK/deletion/current lineage |
| `RAW_COMPLETE_V1_ENTITYSET_MAPPING.csv` | 38 composite mappings, current names, qualified keys, 2 control-only lineage mappings |
| `RAW_COMPLETE_V1_ER_DIAGRAM.md` | Actual 32-sheet relations, conditional/external/binary semantics, excluded entities |
| `RAW_COMPLETE_V1_IMPORT_PLAN.md` | Re-audit first, current replacement, batch/rollback/capacity gates, Phase 1/2 |
| `RAW_COMPLETE_V1_VALIDATION_MATRIX.csv` | 171 executable checks with explicit severity/mode/evidence/pass/failure/rollback |
| `RAW_COMPLETE_V1_OPEN_QUESTIONS.md` | Exact blocker classification and test packages; 14-field disposition |
| `RAW_COMPLETE_V1_DECISION_REPORT.md` | Раздел `REVISION AFTER RED-TEAM AUDIT`, statuses, before/after counts, blockers; no approval |

Новый документ: `RAW_COMPLETE_V1_REVISION_REPORT.md`. Red-team audit не изменялся.

## 5. Исключённые, объединённые и переименованные sheets

| Исходный sheet | Решение | Исходный source/mapping | Новый target/evidence | Потеря source data |
|---|---|---|---|---|
| `RAW_PACKAGE_ITEMS` | EXCLUDE PHYSICAL (PREMATURE) | `Catalog_УпаковкиЕдиницыИзмерения`, child role; 0 confirmed rows | Control-only zero-row/reference test в `RAW_EXTRACTION_RUNS`; raw `Упаковка_Key` остаётся в owning source sheets | Нет |
| `RAW_STOCK_TOTALS` | REMOVE PHYSICAL (DUPLICATIVE) | Derived from stock balances | `CTRL-STOCK-TOTAL` output для `RAW_CURRENT_STOCK`; control-only mapping сохранён | Нет; total воспроизводим |
| `RAW_PRICE_SNAPSHOT` | RENAME/CLARIFY | `InformationRegister_ЦеныНоменклатуры_RecordType` | `RAW_CURRENT_PRICES` | Нет |
| `RAW_STOCK_BALANCES` | RENAME/RECLASSIFY | `AccumulationRegister_СвободныеОстатки_RecordType` | `RAW_CURRENT_STOCK` | Нет; input-set lineage заменяет false source-row provenance |

Активная классификация: **19 REQUIRED + 13 JUSTIFIED_OPTIONAL = 32**. Активных PREMATURE/DUPLICATIVE sheets — **0**.

## 6. Решение по 14 неподтверждённым полям

| Бывшее physical field | Решение | Основание |
|---|---|---|
| `RAW_CLASSIFICATIONS.full_path_raw` | REMOVE | Нет source; path относится к derivation вне RAW |
| `RAW_PRODUCT_CLASSIFICATIONS.is_primary_raw` | REMOVE | Нет source/rule |
| `RAW_PRICE_TYPES.currency_id_raw` | REMOVE | Нет source property в этом EntitySet |
| `RAW_PRODUCT_FILES.file_role_raw` | REMOVE | Role не опубликован; не угадывается |
| `RAW_VARIANT_FILES.file_role_raw` | REMOVE | Role не опубликован; не угадывается |
| `RAW_DESCRIPTIONS.language_code` | TECHNICAL_REQUIRED | `CONSTANT(und)`, без language inference |
| `RAW_DESCRIPTIONS.active_status_raw` | REMOVE | Нет source |
| `RAW_ATTRIBUTE_DEFINITIONS.unit_raw` | REMOVE | Нет source |
| `RAW_ATTRIBUTE_VALUES.value_type_raw` | REMOVE | Source value имеет подтверждённый Boolean type |
| `RAW_MARKETPLACE_CONTENT.language_code` | TECHNICAL_REQUIRED | `CONSTANT(und)`, без language inference |
| `RAW_MARKETPLACE_IMAGES.image_reference_raw` | REMOVE | Нет source |
| `RAW_PRODUCT_RELATIONS.source_variant_id` | REMOVE | Нет source |
| `RAW_PRODUCT_RELATIONS.target_variant_id` | REMOVE | Нет source |
| `RAW_PRODUCT_RELATIONS.relation_value_raw` | REMOVE | Нет source |

Результат: **0 physical `UNCONFIRMED_SOURCE` fields**. Open Questions может описывать неизвестный future source, но такой header не входит в physical v1.

## 7. Current prices/current stock

### `RAW_CURRENT_PRICES`

- Grain: product + `variant_id_raw` + price type at one cutoff.
- Selection: latest source `Period <= cutoff` по versioned deterministic rule.
- Source zero GUID сохраняется; typed variant FK nullable.
- Baseline ≈62 878, upper envelope 91 140; точное число — PHASE_1_BLOCKER.
- Новый validated snapshot атомарно заменяет previous current snapshot.

### `RAW_CURRENT_STOCK`

- Grain: product + variant + warehouse at one cutoff.
- Quantity: signed sum source movements by versioned rule.
- Upper envelope: 72 912 rows = 9 114 variants × 8 warehouses, включая explicit zero rows.
- Lineage: cutoff + aggregation rule + source count + canonical input checksum.
- `stock_total` вычисляется в validation output и не заменяет warehouse detail.

`RAW_EXTRACTION_RUNS` append-only хранит историю запусков. Daily price/stock rows не append в current sheets. Предыдущий approved state может существовать только как отдельный frozen export. Future live read-only verification цены/остатка перед заказом зафиксирована, но не реализована.

## 8. Изменения Validation Matrix

| Показатель | До | После |
|---|---:|---:|
| Validations | 169 | 171 |
| Impossible as written | 6 | 0 известных после revision |
| Severity | P0/P1, все blocking | 168 BLOCKING / 3 WARNING |
| Execution mode | Неявно через import plan | 155 AUTOMATIC_EACH_LOAD / 16 AUTOMATIC_FIRST_LOAD |
| Required contract columns | Старый evidence/stop format | 11 явных columns, включая pass/failure/rollback |

Сохранены/добавлены controls: PK, GUID, FK coverage, orphan, source duplicates, leading zeros, HTML, explicit zeros, stock-total reconciliation, idempotency, no-photo retention/no substitution, raw color names, unknown headers, expected/extracted/validated/rejected/missing accounting, owner/binary polymorphic typing и required-null profile.

## 9. Новый расчёт Google Sheets

Формула каждого physical sheet: `(capacity rows + 1 header) × fields`.

| Layer | Sheets | Fields | Cells |
|---|---:|---:|---:|
| TECHNICAL | 4 | 47 | 2 090 |
| METADATA | 2 | 38 | 10 898 |
| CORE | 9 | 145 | 148 753 |
| COMMERCIAL | 4 | 52 | 2 539 465 |
| MEDIA | 6 | 87 | 303 777 |
| CONTENT | 3 | 38 | 82 747 |
| MARKETPLACE | 3 | 49 | 293 883 |
| RELATIONS | 1 | 10 | 60 |
| **Итого** | **32** | **466** | **3 381 673** |

- Официальный limit: 10 000 000 cells.
- Практический ориентир регулярно обновляемого проекта: 2–3 млн used cells.
- v1 upper envelope: 3 381 673 cells.
- Stop/review: projected >3,5 млн, >50 000 chars/cell или неисполняемый refresh SLA.
- Обязательны payload target ≤2 MB, batch/backoff/timeout, actual used range, no binary/Base64 и no workbook-wide/full-column formulas.
- Для 10 000 products / 100 000 variants требуется PostgreSQL или BigQuery; migration вне scope.

## 10. Оставшиеся открытые вопросы

| Класс | Количество | Вопросы |
|---|---:|---|
| BLOCKER | 1 | Независимый re-audit и owner decision |
| PHASE_1_BLOCKER | 3 | Variant-file closure/count; current-price exact count; required-null profile |
| PHASE_2_BLOCKER | 1 | Full Ozon mapping traversal/count |
| RESOLVED_BY_TEST_EXTRACTION | 1 | Palette count/referenced closure package |
| NON_BLOCKING | 6 | File roles, language semantics, marketplace category paths, package-key role, binary coverage, external relation targets |

Итого remaining blocker-class questions: **5**. Exact EntitySet/test package, expected result, success criterion и обновляемый документ находятся в Open Questions.

## 11. Проверки согласованности

Автоматический self-check: **PASS**.

| Проверка | Результат |
|---|---|
| CSV import через spreadsheet runtime | PASS: Dictionary `A1:V467`, Mapping `A1:P39`, Validation `A1:K172` |
| Уникальность CSV headers | PASS |
| Dictionary composite keys | PASS: 466/466 unique |
| Mapping composite keys | PASS: 38/38 unique |
| Validation IDs | PASS: 171/171 unique |
| Physical sheets/fields | PASS: 32/466 |
| Physical `UNCONFIRMED_SOURCE` | PASS: 0 |
| All target sheets | PASS |
| All declared FK | PASS: target exists, target is key, data type compatible |
| Table-qualified validation inputs | PASS |
| Removed/old sheets in active CSV contract | PASS: 0 |
| Removed fields in Dictionary/Validation | PASS: 0 |
| ER coverage | PASS: все 32 active sheets представлены |
| Per-sheet cell arithmetic | PASS: 32/32; total 3 381 673 |
| Backup integrity | PASS: 8/8 original hashes match |
| Red-team audit integrity | PASS: SHA unchanged |

Ни Google Sheets, ни ETL, ни CURRENT RAW, ни production, ни AI Seller в рамках revision не изменялись. Git commit/push не выполнялся.

## 12. SHA-256 до и после

| Документ | До revision | После revision |
|---|---|---|
| Architecture | `1594357250144d134a2f0a411ff0bce224ecc4e583d65ccf8fa1aad1f1f9d1b7` | `3f851dde2673fd874f678ecd21eb897819b155ca0c5b66e499e726873ad48b93` |
| Data Dictionary | `ef441169f3096368e2e73564d3355b50282ef459b220f65d6744a4604e48bdeb` | `1e17b83204b94b94d038ff38764ce2a9c1aab466361f20116ecfa8d2c2ba0985` |
| EntitySet Mapping | `e42b635474b24e106acaa1e6af648313a6b6eb5a9eb8a262f72f61e1d873064c` | `67a0d9c89833b72231f68c0940f6fac47b16bdf2f0e74afd2375915f3938edb9` |
| ER Diagram | `316a3cff5b7dba70da827bb9f71897df6843c371cbcbd041c6ada92d71105f81` | `ce12021861163bd06fbbb911e66215c887bbe0be69c447548985ff6a62f8b25f` |
| Import Plan | `1ae9601e6d0564b16d10bbe62b485f0de0a2fc3e3474a3a0e7277aea4f08e8f1` | `c48413d1ac9cbd13ae3db0ec1da7b3f5c0df7c78b84e3b1b2d983f8d00576843` |
| Validation Matrix | `fc4519e9e323580aec447cd13063bfe144df1e30d3dea6515720e5e88eb7834a` | `3872e00114a00bcee6a45f9d3abd4e2217cbff07cca2181ffd3053d1b6fa27b0` |
| Open Questions | `ebc1552c29e9738f10b4d203da3f4d005b9a69cd79715628e05eb7fd1cfc6c1b` | `c3c1f9b10787549f269f2842df777627dbd24b381197f1998573f048be135495` |
| Decision Report | `89e366cf54f7fc72d8f7d017b130ea3fcc1dc12e46637f6176a51a2a816a7a2b` | `398b7458023ad6949255ae1a460b3d57eef67b20f4cde7b27538782794538ea5` |

Backup: `PRE_REVISION_BACKUP/`.  
Red-team audit SHA-256: `97f003bad7b9331e695ece6c6f715a638a3e0099054edf0ea29b35335bacebe0` (unchanged).

## 13. Точный scope повторного red-team аудита

### Вход

1. Восемь revised документов контракта.
2. Этот Revision Report.
3. Неизменённый `RAW_COMPLETE_V1_RED_TEAM_AUDIT.md` как baseline.
4. `PRE_REVISION_BACKUP` и SHA table для доказательства change scope.

### Обязательная проверка

1. Повторно проверить закрытие C1–C4 по физическим CSV, а не только по текстовым заявлениям.
2. Проверить disposition всех 10 minor issues и 14 former unconfirmed fields.
3. Подтвердить 32 sheets / 466 fields / 38 mappings / 171 validations.
4. Подтвердить отсутствие active PREMATURE/DUPLICATIVE sheets и корректность двух control-only lineage mappings.
5. Проверить все FK, namespace/polymorphic/nullable semantics и отсутствие orphan-by-contract.
6. Проверить исполнимость каждой validation, severity, execution mode, required inputs, pass/failure/rollback.
7. Проверить current-price/current-stock atomic replacement, explicit zero rows, stock-total validation output и запрет daily append.
8. Независимо пересчитать capacity 3 381 673 и проверить Google Sheets operating gates.
9. Проверить согласованность Architecture, Dictionary, Mapping, ER, Import Plan, Validation Matrix, Open Questions и Decision Report.
10. Подтвердить, что Decision Report не объявляет owner approval/implementation readiness.

### Вне scope повторного статического аудита

- Новый широкий OData discovery.
- Live test extraction и закрытие execution counts.
- Создание Google Sheets.
- ETL/code implementation.
- Изменение CURRENT RAW, production или AI Seller.
- Git commit/push.

### Ожидаемый результат

Новый независимый verdict по revised contract с отдельным списком unresolved contract defects и readiness/execution blockers. Owner approval возможен только отдельным решением после успешного независимого verdict и закрытия соответствующих Phase blockers.

