# RAW COMPLETE v1 — архитектурный контракт

Статус: **DRAFT FOR OWNER APPROVAL**  
Дата: 2026-07-17  
Область: активная категория «Пряжа», 204 товара / 9 114 характеристик.  
AI Seller использует RAW COMPLETE напрямую: **NO**.

## 1. Границы

- **CURRENT RAW** — существующий неизменяемый Google snapshot из 24 столбцов. Не обновляется и не переписывается этим проектом.
- **RAW COMPLETE v1** — отдельное техническое извлечение подтверждённых опубликованных источников 1С, без AI-догадок и без улучшения контента.
- **NORMALIZATION RULES** — только детерминированные преобразования ключей, типов, snapshots и контроля качества; исходное значение сохраняется рядом или в исходном листе.
- **IDEAL** — будущий слой. В этот контракт не входит.

Запрещены в RAW COMPLETE: AI confidence, AI-generated value, продающие описания, softness, warmth, recommended projects, экспертные ограничения и любые свойства без самостоятельного подтверждённого источника 1С.

## 2. Физическая модель

Предлагается **34 физических листа** и **514 полей**. Каждый лист имеет самостоятельную сущность и гранулярность строки. Прямые стабильные реквизиты хранятся колонками; EAV применяется только для опубликованных web-фильтров.

| Layer | Листов | Полей | Оценка ячеек |
|---|---|---|---|
| TECHNICAL | 4 | 47 | 2 000 |
| METADATA | 2 | 38 | 9 998 |
| CORE | 10 | 167 | 157 995 |
| COMMERCIAL | 5 | 61 | 2 539 474 |
| MEDIA | 6 | 96 | 336 416 |
| CONTENT | 3 | 44 | 115 012 |
| MARKETPLACE | 3 | 49 | 291 921 |
| RELATIONS | 1 | 12 | 72 |

### Каталог листов и ёмкость

Оценка использует верхнюю границу для цен, остатков и бинарных метаданных; это capacity envelope, а не обещание фактического числа строк.

| Layer | Физический лист | Гранулярность | Ожидаемые строки | Колонки | Ячейки (оценка) |
|---|---|---|---|---|---|
| TECHNICAL | RAW_SOURCE_SYSTEMS | one row per logical source system | 3 | 8 | 32 |
| TECHNICAL | RAW_SCHEMA_VERSIONS | one row per frozen RAW COMPLETE schema version | 1 at v1 freeze | 9 | 18 |
| TECHNICAL | RAW_EXTRACTION_RUNS | one row per EntitySet extraction attempt | approximately 30-45 per full run | 18 | 738 |
| TECHNICAL | RAW_EXTRACTION_ERRORS | one row per safe extraction/validation error | 0 on successful freeze; dynamic | 12 | 1 212 |
| METADATA | RAW_DATA_DICTIONARY | one row per physical field in RAW COMPLETE v1 | equal to field count in this contract | 22 | 9 262 |
| METADATA | RAW_ENTITYSET_MAPPING | one row per source-to-target mapping | approximately 40 mappings | 16 | 736 |
| CORE | RAW_PRODUCTS | one row per active-scope nomenclature item | 204 | 56 | 11 480 |
| CORE | RAW_VARIANTS | one row per 1C characteristic/color variant | 9,114 | 15 | 136 725 |
| CORE | RAW_CLASSIFICATIONS | one row per category node within a named source classification system | at least 33 confirmed nodes; marketplace nodes dynamic | 17 | 1 717 |
| CORE | RAW_PRODUCT_CLASSIFICATIONS | one row per product-to-source-category relation | 407 confirmed core relations plus marketplace relations when validated | 9 | 7 209 |
| CORE | RAW_MANUFACTURERS | one row per manufacturer referenced by yarn products | 15 | 8 | 128 |
| CORE | RAW_UNIT_DEFINITIONS | one row per unit referenced by scoped products/package records | at least 3 referenced units; close transitively | 16 | 336 |
| CORE | RAW_PACKAGE_SETS | one row per package set referenced by scoped products | 1 | 10 | 20 |
| CORE | RAW_PACKAGE_ITEMS | one row per package item owned by a scoped package set | 0 confirmed for the referenced set; retain empty sheet contract | 20 | 220 |
| CORE | RAW_WAREHOUSES | one row per warehouse referenced in scoped stock | 8 warehouses represented in CURRENT RAW; validate against source | 8 | 72 |
| CORE | RAW_PRICE_TYPES | one row per referenced price type | 10 confirmed | 8 | 88 |
| COMMERCIAL | RAW_PRICE_SNAPSHOT | one row per product + variant + price type at extraction cutoff | up to 91,140 (9,114 variants × 10 price types); actual non-empty count must be measured | 15 | 1 367 115 |
| COMMERCIAL | RAW_STOCK_BALANCES | one row per product + variant + warehouse at extraction cutoff | up to 72,912 (9,114 variants × 8 warehouses), including explicit zero rows | 13 | 947 869 |
| COMMERCIAL | RAW_STOCK_TOTALS | one row per product + variant at extraction cutoff | 9,114 | 10 | 91 150 |
| COMMERCIAL | RAW_BARCODES | one row per published barcode relation | 14,295 | 9 | 128 664 |
| COMMERCIAL | RAW_SUPPLIER_ITEMS | one row per supplier nomenclature record | 333 | 14 | 4 676 |
| MEDIA | RAW_VARIANT_IMAGE_LINKS | one row per product-characteristic image-link record | 6,173 | 14 | 86 436 |
| MEDIA | RAW_COLOR_SCHEMES | one row per referenced 1C color scheme | 886 | 13 | 11 531 |
| MEDIA | RAW_COLOR_PALETTES | one row per palette referenced by color schemes | 20 referenced palettes observed; exact extraction validation required | 12 | 252 |
| MEDIA | RAW_PRODUCT_FILES | one row per attached product file | 445 | 21 | 9 366 |
| MEDIA | RAW_VARIANT_FILES | one row per attached characteristic-image file referenced by image links | up to 6,170 referenced file GUIDs; exact entity-row count not yet extracted | 21 | 129 591 |
| MEDIA | RAW_BINARY_STORAGE_METADATA | one row per attached file composite storage key; no binary/Base64 | up to 6,615 referenced product+variant files before deduplication | 15 | 99 240 |
| CONTENT | RAW_DESCRIPTIONS | one row per owner + description type + source record | 316 potential rows: 204 direct + 56 plain + 56 HTML; 309 currently non-empty | 15 | 4 755 |
| CONTENT | RAW_ATTRIBUTE_DEFINITIONS | one row per referenced web-filter definition or parent definition | up to 503 referenced rows before GUID deduplication: 480 values + 23 parents | 16 | 8 064 |
| CONTENT | RAW_ATTRIBUTE_VALUES | one row per product + web-filter definition source record | 7,860 | 13 | 102 193 |
| MARKETPLACE | RAW_MARKETPLACE_LISTINGS | one row per source marketplace listing/mapping record | 4,910 Kaspi + 2,408 currently extracted Ozon mappings; Ozon extraction incomplete | 20 | 146 380 |
| MARKETPLACE | RAW_MARKETPLACE_CONTENT | one row per marketplace listing content record | 4,910 Kaspi content rows; Ozon content source UNCONFIRMED | 15 | 73 665 |
| MARKETPLACE | RAW_MARKETPLACE_IMAGES | one row per listing image line | 5,133 Kaspi image rows; Ozon image source UNCONFIRMED | 14 | 71 876 |
| RELATIONS | RAW_PRODUCT_RELATIONS | one row per explicit source product relation | 5 explicit recommendation links | 12 | 72 |

**Итого верхняя оценка:** 3 452 888 ячеек.

## 3. Ключи и provenance

Для каждой предметной записи сохраняются: source_system_id, source_entityset, source_record_id и extraction_run_id. Поле напрямую соответствует реквизиту EntitySet, поэтому тяжёлый field-level provenance не создаётся. Если строка является snapshot/derived, правило преобразования и cutoff фиксируются в самой строке и в RAW_EXTRACTION_RUNS.

GUID и коды всегда текстовые. Ведущие нули не преобразуются в числа. PK не переиспользуются между classification systems или marketplaces: применяется namespace-qualified technical key.

## 4. Цена и остаток

Опубликованная OData отдаёт историю цен и движения остатков, а не готовые SliceLast/Balance. Полная операционная история не является Product Knowledge и не помещается безопасно в один Google Sheets: ранее обработано 322 849 ценовых записей и 1 104 986 движений.

RAW COMPLETE хранит:

- RAW_PRICE_SNAPSHOT — последнюю запись по product + variant + price type на cutoff;
- RAW_STOCK_BALANCES — документированную сумму движений по product + variant + warehouse на cutoff, включая нули;
- RAW_STOCK_TOTALS — сумму складских остатков по варианту для контроля.

Алгоритм, cutoff, исходный EntitySet, число входных записей и checksum обязательны. Внешнему клиенту сведения о виртуальных складах не предназначены.

## 5. Descriptions

RAW_DESCRIPTIONS не очищает HTML и не переписывает текст. Прямое описание номенклатуры, website plain text и website HTML — разные строки. Marketplace-контент хранится отдельно. language_code = und, если язык не опубликован; язык не угадывается по содержимому.

## 6. Media

Base64 и бинарные данные запрещены в Google Sheets. Хранятся GUID, owner, extension, size, storage type, safe retrieval key, MIME после проверки magic bytes и SHA-256 при фактическом чтении.

Подтверждённая цепочка:

PRODUCT → VARIANT → RAW_VARIANT_IMAGE_LINKS → RAW_COLOR_SCHEMES → RAW_VARIANT_FILES → RAW_BINARY_STORAGE_METADATA.

Цветовая схема, логическая связь, file metadata и binary metadata остаются разными сущностями.

## 7. Classification

RAW_CLASSIFICATIONS использует classification_system, поэтому 1C group, web category, Kaspi/Ozon category никогда не сливаются. Единую AI-категорию v1 не создаёт. RAW_PRODUCT_CLASSIFICATIONS хранит только подтверждённые связи.

Отдельный RAW_COUNTRIES не создаётся: продукт публикует Страна как текст, но подтверждённого FK к Catalog_СтраныМира нет. Создание связи было бы выдумкой. country_raw остаётся в RAW_PRODUCTS.

## 8. Marketplace

RAW_MARKETPLACE_LISTINGS, RAW_MARKETPLACE_CONTENT и RAW_MARKETPLACE_IMAGES имеют platform-qualified keys. Kaspi подтверждён полностью для текущей выборки. Ozon mapping включён с PARTIAL baseline и требует завершения малых batches. Halyk/Beru не добавляются как заполненные источники: для пряжи получено 0 записей. Добавление новой площадки не меняет PK основных листов.

## 9. Google Sheets capacity

Официальный предел Google Sheets — 10 млн ячеек на файл; также ячейка длиннее 50 000 символов удаляется при конвертации. Источник: https://support.google.com/drive/answer/37603?hl=en.

Текущая верхняя оценка 3 452 888 ячеек помещается в один файл, но крупные листы необходимо создавать ровно под фактический used range. Проверенные максимумы контента: product description 1 949 символов, website HTML 4 590, Kaspi description 1 024 — ниже 50 000.

При 10 000 товарах / 100 000 характеристиках модель даёт ориентировочно 42 851 194 ячеек и выходит за предел одного Google Sheets. Практический триггер PostgreSQL/BigQuery: прогноз >7 млн ячеек до загрузки, любой лист >250 000 строк с частыми refresh, либо невозможность завершить полный upsert+validation в согласованное окно. Это операционный порог проекта, не официальный лимит Google.

## 10. Явные исключения v1

- Полная история документов, движений, себестоимости и продаж.
- Binary/Base64 payload.
- AI/экспертные свойства будущего IDEAL.
- Незаполненные дополнительные реквизиты товаров и характеристик.
- ABC/XYZ и сегменты: аналитика, частичная выборка, не стабильный Product Knowledge.
- Halyk/Beru/Wildberries как заполненные площадки.
- Неподтверждённые Ozon descriptions/images.

## 11. Acceptance

Контракт может перейти в OWNER_APPROVED только после проверки восьми документов владельцем. Это не разрешает переключение AI Seller. Реализация должна остановиться после фиксации RAW COMPLETE v1 и отдельного quality report.
