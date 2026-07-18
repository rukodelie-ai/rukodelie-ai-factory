# RAW COMPLETE v1 — архитектурный контракт после red-team revision

Статус: **REVISED — NOT OWNER APPROVED**  
Дата ревизии: 2026-07-18  
Область: активная категория «Пряжа», 204 товара / 9 114 характеристик.  
Исходный red-team verdict: **C. REVISE BEFORE APPROVAL**.  
AI Seller использует RAW COMPLETE напрямую: **NO**.

## 1. Границы

- **CURRENT RAW** — существующий неизменяемый Google snapshot из 24 столбцов. Этот контракт его не обновляет.
- **RAW COMPLETE v1** — отдельный source-close current snapshot подтверждённых опубликованных источников 1С и необходимая техническая provenance.
- **CURRENT SNAPSHOT RULES** — детерминированный выбор текущей цены и расчёт текущего остатка выполняются в staging до атомарной замены соответствующего листа.
- **IDEAL** — будущий отдельный слой. В этот контракт не входит.

В RAW COMPLETE запрещены AI confidence, AI-generated values, продающие описания, softness, warmth, recommended projects и любые экспертные/бизнес-интерпретации без самостоятельного источника.

После ревизии физическая схема содержит **0 полей `UNCONFIRMED_SOURCE`**. Multi-source sheets выбирают точную property по `source_entityset` строки и `source_role` из EntitySet Mapping.

## 2. Физическая модель

Активная схема v1: **32 физических листа, 466 полей, 38 mappings и 171 validation**.

- `RAW_PACKAGE_ITEMS` исключён: подтверждено 0 scoped rows; вопрос типа `Упаковка_Key` остаётся в Open Questions.
- `RAW_STOCK_TOTALS` исключён: `stock_total` является воспроизводимым validation output.
- `RAW_PRICE_SNAPSHOT` переименован в `RAW_CURRENT_PRICES`.
- `RAW_STOCK_BALANCES` переименован в `RAW_CURRENT_STOCK`; aggregate lineage хранит cutoff, input count и input checksum вместо фиктивной одной source record.
- Два исходных mapping исключённых/объединённых sheets сохранены как **control-only lineage**, а не как физические таблицы: package-child zero-row/reference test фиксируется в `RAW_EXTRACTION_RUNS`; `stock_total` — в validation output `RAW_CURRENT_STOCK`.

| Layer | Листов | Полей | Capacity cells |
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

### Каталог листов, очередь и ёмкость

Capacity использует верхнюю границу и включает строку заголовков: `(capacity rows + 1) × fields`. `REQUIRED` обязателен для полного ядра; `JUSTIFIED_OPTIONAL` сохраняется в контракте, но не блокирует первую предметную загрузку.

| Layer | Physical sheet | Capacity rows | Fields | Cells | Класс | Queue |
|---|---|---:|---:|---:|---|---|
| TECHNICAL | RAW_SOURCE_SYSTEMS | 3 | 8 | 32 | REQUIRED | PHASE 1 |
| TECHNICAL | RAW_SCHEMA_VERSIONS | 1 | 9 | 18 | REQUIRED | PHASE 1 |
| TECHNICAL | RAW_EXTRACTION_RUNS | 45 | 18 | 828 | REQUIRED | PHASE 1 |
| TECHNICAL | RAW_EXTRACTION_ERRORS | 100 | 12 | 1 212 | JUSTIFIED_OPTIONAL | PHASE 1 |
| METADATA | RAW_DATA_DICTIONARY | 466 | 22 | 10 274 | JUSTIFIED_OPTIONAL | PHASE 1 |
| METADATA | RAW_ENTITYSET_MAPPING | 38 | 16 | 624 | JUSTIFIED_OPTIONAL | PHASE 1 |
| CORE | RAW_PRODUCTS | 204 | 57 | 11 685 | REQUIRED | PHASE 1 |
| CORE | RAW_VARIANTS | 9 114 | 14 | 127 610 | REQUIRED | PHASE 1 |
| CORE | RAW_CLASSIFICATIONS | 100 | 16 | 1 616 | REQUIRED | PHASE 1 |
| CORE | RAW_PRODUCT_CLASSIFICATIONS | 800 | 9 | 7 209 | REQUIRED | PHASE 1 |
| CORE | RAW_MANUFACTURERS | 15 | 8 | 128 | REQUIRED | PHASE 1 |
| CORE | RAW_UNIT_DEFINITIONS | 20 | 16 | 336 | REQUIRED | PHASE 1 |
| CORE | RAW_PACKAGE_SETS | 1 | 10 | 20 | JUSTIFIED_OPTIONAL | PHASE 2 |
| CORE | RAW_WAREHOUSES | 8 | 8 | 72 | REQUIRED | PHASE 1 |
| CORE | RAW_PRICE_TYPES | 10 | 7 | 77 | REQUIRED | PHASE 1 |
| COMMERCIAL | RAW_CURRENT_PRICES | 91 140 | 16 | 1 458 256 | REQUIRED | PHASE 1 |
| COMMERCIAL | RAW_CURRENT_STOCK | 72 912 | 13 | 947 869 | REQUIRED | PHASE 1 |
| COMMERCIAL | RAW_BARCODES | 14 295 | 9 | 128 664 | JUSTIFIED_OPTIONAL | PHASE 2 |
| COMMERCIAL | RAW_SUPPLIER_ITEMS | 333 | 14 | 4 676 | JUSTIFIED_OPTIONAL | PHASE 2 |
| MEDIA | RAW_VARIANT_IMAGE_LINKS | 6 173 | 14 | 86 436 | REQUIRED | PHASE 1 |
| MEDIA | RAW_COLOR_SCHEMES | 886 | 13 | 11 531 | REQUIRED | PHASE 1 |
| MEDIA | RAW_COLOR_PALETTES | 20 | 12 | 252 | JUSTIFIED_OPTIONAL | PHASE 2 |
| MEDIA | RAW_PRODUCT_FILES | 445 | 17 | 7 582 | JUSTIFIED_OPTIONAL | PHASE 2 |
| MEDIA | RAW_VARIANT_FILES | 6 170 | 16 | 98 736 | REQUIRED | PHASE 1 |
| MEDIA | RAW_BINARY_STORAGE_METADATA | 6 615 | 15 | 99 240 | JUSTIFIED_OPTIONAL | PHASE 2 |
| CONTENT | RAW_DESCRIPTIONS | 316 | 14 | 4 438 | REQUIRED | PHASE 1 |
| CONTENT | RAW_ATTRIBUTE_DEFINITIONS | 503 | 15 | 7 560 | REQUIRED | PHASE 1 |
| CONTENT | RAW_ATTRIBUTE_VALUES | 7 860 | 9 | 70 749 | REQUIRED | PHASE 1 |
| MARKETPLACE | RAW_MARKETPLACE_LISTINGS | 7 318 | 21 | 153 699 | JUSTIFIED_OPTIONAL | PHASE 2 |
| MARKETPLACE | RAW_MARKETPLACE_CONTENT | 4 910 | 16 | 78 576 | JUSTIFIED_OPTIONAL | PHASE 2 |
| MARKETPLACE | RAW_MARKETPLACE_IMAGES | 5 133 | 12 | 61 608 | JUSTIFIED_OPTIONAL | PHASE 2 |
| RELATIONS | RAW_PRODUCT_RELATIONS | 5 | 10 | 60 | JUSTIFIED_OPTIONAL | PHASE 2 |

Итого после исправления: **19 REQUIRED + 13 JUSTIFIED_OPTIONAL = 32**. Активных PREMATURE и DUPLICATIVE sheets нет.

## 3. Ключи, типы и provenance

- `RAW_DATA_DICTIONARY` PK: `(sheet_name, field_name)`.
- `RAW_ENTITYSET_MAPPING` PK: `(target_sheet, source_entityset, source_role)`.
- Classification FK всегда ведёт на namespaced `classification_id`; исходный category GUID/text сохраняется отдельно.
- Marketplace parent/child sheets используют один `listing_id = DERIVE(platform, source_listing_id)` и отдельно сохраняют raw source ID.
- Binary link использует `binary_storage_id = DERIVE(file_id, exact file_type_raw)`; `file_id` без type не считается FK.
- Полиморфный `Owner` варианта сохраняется как `owner_raw`; `product_id` типизируется только при точном `owner_type_raw`.
- External recommendation target сохраняется в `target_product_source_id`; in-scope FK nullable и не уничтожает внешний source GUID.
- GUID и коды записываются как текст; ведущие нули не преобразуются в числа.

Direct source rows сохраняют `source_system_id`, точный `source_entityset`, `source_record_id` и `extraction_run_id`. `RAW_CURRENT_STOCK` агрегирует множество movement rows и поэтому вместо одной фиктивной source record хранит `source_record_count`, `input_checksum_sha256`, cutoff и aggregation rule.

## 4. Current prices и current stock

### RAW_CURRENT_PRICES

- Одна строка на product + source variant key + price type.
- Выбирается максимальный `Period <= cutoff`.
- `variant_id_raw` сохраняет zero GUID; typed `variant_id` становится null для product-level price.
- Текущий baseline: 62 878 непустых комбинаций; capacity envelope: 91 140.
- Новый validated snapshot атомарно заменяет предыдущий current snapshot; daily append запрещён.

### RAW_CURRENT_STOCK

- Одна строка на product + variant + warehouse.
- `quantity_available = SUM(Receipt − Expense)` через единый cutoff и versioned aggregation rule.
- Полная матрица 9 114 × 8 = 72 912 строк сохраняет явные нули и все виртуальные склады.
- `stock_total` не заменяет warehouse rows и не хранится отдельным дублирующим листом. Он воспроизводится как `SUM(quantity_available) GROUP BY product_id, variant_id` и фиксируется в validation output.
- Клиенту сведения о виртуальных складах не передаются.

`RAW_EXTRACTION_RUNS` хранит историю запусков, а не историю каждой цены/остатка. Прошлый утверждённый state при необходимости сохраняется как отдельный frozen export. Аналитическая price/stock history находится вне Google Sheets RAW COMPLETE v1.

Перед будущим подтверждением заказа потребуется live read-only проверка цены и остатка в 1С. Это требование зафиксировано, но в текущей задаче не реализуется.

## 5. Content и media

- Source descriptions и HTML сохраняются побайтно/посимвольно без очистки; `language_code=und` — детерминированный technical placeholder, не языковая догадка.
- Base64 и binary payload запрещены в Google Sheets.
- MIME/hash хранятся только в `RAW_BINARY_STORAGE_METADATA`, а не дублируются в file sheets.
- Подтверждённая exact цепочка:

`PRODUCT → VARIANT → RAW_VARIANT_IMAGE_LINKS → RAW_COLOR_SCHEMES → RAW_VARIANT_FILES → RAW_BINARY_STORAGE_METADATA`.

Варианты без фотографии не удаляются и не получают подставное фото.

## 6. Google Sheets operating contract

Официальный предел — 10 000 000 cells/spreadsheet; cells длиннее 50 000 characters недопустимы при конвертации. Источник: https://support.google.com/drive/answer/37603?hl=en.

Практический рекомендуемый объём проекта:

- регулярно обновляемый workbook: ориентир **2–3 млн used cells**;
- этот frozen/read-mostly v1: расчётный upper envelope **3 381 673 cells**;
- stop/review до полной загрузки при прогнозе **>3,5 млн cells** или невозможности уложиться в согласованное refresh window.

Условия применения:

1. Один current snapshot; daily price/stock history не накапливается.
2. Binary/Base64 отсутствуют.
3. Values пишутся batch operations с фактическим payload target ≤2 MB, retry/backoff и timeout handling.
4. Создаётся только фактический used range; пустые сотни тысяч строк не резервируются.
5. Нет workbook-wide, volatile и full-column formulas; joins/checksums/validation выполняются вне Sheets.
6. HTML хранится как raw text и не обрабатывается формулами.
7. До full load проверяются projected cells, longest cell и per-sheet rows.
8. Headers и source sheets защищаются от ручного изменения.

Для масштаба 10 000 товаров / 100 000 вариантов PostgreSQL или BigQuery становится обязательным будущим хранилищем. Миграция не входит в v1.

## 7. Phased implementation

- **PHASE 1:** обязательное товарное ядро — товары, варианты, справочники, current prices, current stock, exact variant photos, descriptions и web filters; технические metadata/error sheets могут быть созданы одновременно, но не являются предметным blocker.
- **PHASE 2:** package set, barcodes, suppliers, palettes, product files, binary coverage, relations, Kaspi/Ozon и marketplace content/images.

Все 32 утверждённых headers можно создать после успешного независимого re-audit. Optional означает «не блокирует первую предметную загрузку», а не «не нужен».

## 8. Acceptance

Этот revision не утверждает контракт. Переход к созданию Google Sheets возможен только после:

1. независимого повторного red-team аудита;
2. закрытия PHASE 1 blockers тестовой выгрузкой;
3. owner approval нового Decision Report;
4. подтверждения, что CURRENT RAW, production и AI Seller не затронуты.
