# RAW COMPLETE v1 — финальный red-team аудит реализационного контракта

Дата аудита: 2026-07-18  
Режим: read-only; Google Sheets, ETL, CURRENT RAW, production и AI Seller не изменялись.  
Объект проверки: восемь документов контракта `RAW_COMPLETE_V1_CONTRACT`, локальный снимок опубликованной OData metadata и существующий CURRENT RAW на 9 114 вариантов.

## 1. Executive summary

**Финальный вердикт: C. REVISE BEFORE APPROVAL.**

Контракт содержательно силён: охват источников широк, границы с IDEAL в основном соблюдены, подтверждённая товарно-цветовая фотоцепочка отражена корректно, полная операционная история разумно исключена из Google Sheets. Полного redesign не требуется.

Однако создавать Google Sheets по контракту **как он написан сейчас нельзя**. Обнаружены четыре критических класса проблем:

1. физические PK двух metadata-листов заданы неполно и уже нарушаются самими файлами контракта;
2. рассчитанные остатки и их итог ошибочно объявлены RAW-записями, вследствие чего обязательный record-level provenance невыполним;
3. несколько FK и логических типов не соответствуют ключам/типам источника и дадут orphan или ложную связь;
4. шесть из 169 blocking-проверок невозможно выполнить на объявленной схеме, а план импорта требует остановки при любой P0/P1-ошибке.

Зафиксировано также **10 некритических замечаний**. По листам итог аудита: **18 REQUIRED, 13 JUSTIFIED_OPTIONAL, 2 PREMATURE, 1 DUPLICATIVE**. Все 514 полей обработаны машинно и классифицированы; **14 полей не имеют точного подтверждённого источника**.

Google Sheets для текущего масштаба 204 товара / 9 114 вариантов: **YES, WITH CONDITIONS**. Один read-mostly snapshot до текущей верхней оценки около 3,45 млн ячеек технически допустим. Ежедневное накопление price/stock snapshots в том же файле недопустимо: только эти три коммерческих набора превысят 59 млн ячеек за 30 дней.

**Решение владельца сейчас:** не разрешать Phase A/B; сначала исправить контракт по разделу 13, повторно прогнать red-team checks и только затем утверждать schema-only test load.

### Контрольные итоги

| Показатель | Результат |
|---|---:|
| Физические листы проверены | 34 / 34 |
| Поля проверены | 514 / 514 |
| Source-to-target mappings проверены | 38 / 38 |
| Validation checks проверены | 169 / 169 |
| Критические проблемы | 4 |
| Некритические замечания | 10 |
| Поля без точного источника | 14 |
| Подтверждённые OData EntitySet в предметных mappings | 26 |
| Итог по Google Sheets | YES, WITH CONDITIONS |

## 2. Критические проблемы

### C1. Невалидные физические PK metadata-листов

`RAW_DATA_DICTIONARY` объявляет только `field_name` как `PART` ключа. В фактических 514 строках:

- уникальных `field_name`: 269;
- повторяющихся значений ключа: 62;
- строк, входящих в повторы: 307.

Корректная комбинация `(sheet_name, field_name)` уникальна во всех 514 строках.

`RAW_ENTITYSET_MAPPING` объявляет только `target_sheet` как `PART` ключа. В 38 mappings:

- уникальных `target_sheet`: 34;
- повторяются 4 значения, затрагивая 8 строк: `RAW_CLASSIFICATIONS`, `RAW_PRODUCT_CLASSIFICATIONS`, `RAW_DESCRIPTIONS`, `RAW_MARKETPLACE_LISTINGS`.

Корректная комбинация `(target_sheet, source_entityset, source_role)` уникальна во всех 38 строках.

Последствие: проверки `RAW_DATA_DICTIONARY-PK` и `RAW_ENTITYSET_MAPPING-PK` имеют severity P0 и неизбежно остановят даже идеальную загрузку.

### C2. Нарушена граница RAW/STAGING для остатков

`RAW_STOCK_BALANCES` не является копией source row. `quantity_available` — сумма знаковых движений, а 68 785 нулевых строк синтезируются для полной матрицы variant × warehouse. У такой строки нет одного исходного `source_record_id`. `RAW_STOCK_TOTALS` затем повторно агрегирует уже рассчитанный баланс.

Следствия:

- 13 полей `RAW_STOCK_BALANCES` и 10 полей `RAW_STOCK_TOTALS` относятся к STAGING/current snapshot, а не к RAW;
- обязательные `RAW_STOCK_BALANCES-PROV` и `RAW_STOCK_TOTALS-PROV` невыполнимы;
- `RAW_STOCK_TOTALS` физически дублирует вычислимый результат;
- общий тезис «каждая предметная строка имеет один source_record_id» становится неверным.

`RAW_PRICE_SNAPSHOT` отличается: выбранная строка сохраняет значения одной реальной source record (`Period`, цена, ключи и source record identity). Он может остаться source-close snapshot при явном документировании selection rule и cutoff.

### C3. FK и типы допускают ложные связи или orphan

Критические случаи:

- `RAW_MARKETPLACE_CONTENT.listing_id` и `RAW_MARKETPLACE_IMAGES.listing_id` копируют `Ref_Key` (`Edm.Guid`), но ссылаются на platform-qualified `RAW_MARKETPLACE_LISTINGS.listing_id` (`text`). Эти значения не равны без детерминированного формирования того же namespace key.
- Четыре поля цены/штрихкода/поставщика/marketplace ссылаются на `RAW_PACKAGE_ITEMS.package_item_id`, хотя этот лист имеет 0 подтверждённых строк. Не доказано, что `Упаковка_Key` относится именно к child rows, а не к уже выделенному `RAW_UNIT_DEFINITIONS`.
- `RAW_PRODUCTS.parent_group_id` и `RAW_MARKETPLACE_LISTINGS.category_id_raw` ссылаются на `RAW_CLASSIFICATIONS.source_category_id`, который не является ключом без `classification_system`/namespace.
- `RAW_PRODUCT_FILES.content_hash_sha256` и `RAW_VARIANT_FILES.content_hash_sha256` ссылаются на nullable/non-unique hash, а не на composite binary identity.
- `RAW_VARIANTS.product_id` и `RAW_PACKAGE_ITEMS.package_set_id` объявлены UUID, но их source property `Owner` имеет тип `Edm.String`; тип владельца полиморфный и должен проверяться вместе с `Owner_Type`.
- `RAW_PRICE_SNAPSHOT.variant_id` объявлен `nullable=NO`, хотя контракт одновременно допускает product-level price через zero GUID. Zero GUID не является валидным FK на `RAW_VARIANTS`.
- `RAW_PRODUCT_RELATIONS.target_product_id` ссылается только на 204 yarn products, хотя пять source recommendations могут вести на товары вне yarn scope.
- `RAW_BINARY_STORAGE_METADATA.file_id` — полиморфная ссылка; она валидна только в паре с `file_type_raw`, а не сама по себе.

Также найдено восемь source/type расхождений; они перечислены в разделе 5. До исправления ключей и типов referential validation не является доказательной.

### C4. Validation matrix не исполнима как gate

Все 169 проверок имеют severity P0 или P1 и, согласно import plan, являются blocking. Из них 163 можно автоматизировать, а 6 невозможно выполнить на текущей схеме:

| Check | Причина невозможности |
|---|---|
| `RAW_DATA_DICTIONARY-PK` | ожидает глобальную уникальность `field_name`, которой нет |
| `RAW_ENTITYSET_MAPPING-PK` | ожидает глобальную уникальность `target_sheet`, которой нет |
| `RAW_STOCK_BALANCES-PROV` | aggregate row не имеет одной source record |
| `RAW_STOCK_TOTALS-PROV` | derived total не имеет одной source record |
| `CTRL-NO-SUBSTITUTION` | evidence field указан как `variant_file_id`, но в target sheet поле называется `file_id` |
| `CTRL-URL-SECRET` | evidence field указан как `url_raw`, которого нет; объявлены `url_raw_safe`, `url_redacted`, `url_hash_sha256` |

Следствие: Phase F не может завершиться успешно даже при корректных данных. Это блокер до создания таблицы, а не execution-time detail.

## 3. Некритические замечания

1. Четырнадцать полей `UNCONFIRMED_SOURCE` физически включены в v1; два `language_code` при этом `nullable=NO`, что противоречит отсутствию source property.
2. `RAW_PACKAGE_ITEMS` проектирует 20 полей для 0 подтверждённых строк и является гипотетическим future placeholder.
3. Семь derived-полей дублируют уже доступный source/technical факт: MIME, display order/hash в file sheets и marketplace image position.
4. `RAW_VARIANT_FILES.is_primary_derived` не имеет подтверждённого правила: известный direct primary key относится к product image, не к каждому variant file.
5. Для 29 ORIGINAL-полей используется `MULTIPLE_CONFIRMED` или выражение из нескольких properties; source существует, но field-level соответствие нельзя проверить машинно по одной metadata property.
6. Тридцать восемь обязательных полей строже OData metadata (`nullable=NO` при `Nullable=true`). Это допустимо только после scope-level null profiling и явного reject/null policy.
7. Одинаковое source deletion rule механически назначено 476 полям, включая technical/metadata/derived; у них нет собственного source deletion flag.
8. Оценка 3 452 888 использует 420 dictionary rows вместо 514 и примерно 45 mapping rows вместо 38. Для текущего контракта арифметическая оценка должна быть около **3 454 844**, то есть на 1 956 ячеек выше.
9. Ozon, variant files, palettes и фактический price snapshot count всё ещё имеют pending/partial status; это должно быть явно отражено в readiness, а не названо полностью готовым контрактом.
10. Порог stop только при 7 млн ячеек слишком поздний для регулярно обновляемого и открываемого человеком workbook; не закреплены payload chunking, refresh SLA и запрет workbook-wide formulas/sorts.

## 4. Анализ 34 физических листов

Итог: 18 REQUIRED + 13 JUSTIFIED_OPTIONAL + 2 PREMATURE + 1 DUPLICATIVE = 34.

| sheet_name | Layer | Назначение | Источник | Ожидаемые строки | Почему отдельно | Можно объединить / последствие | Оценка |
|---|---|---|---|---:|---|---|---|
| RAW_SOURCE_SYSTEMS | TECHNICAL | Корень provenance | TECHNICAL | 3 | Реестр логических источников | Нет; иначе source metadata повторяется в runs | REQUIRED |
| RAW_SCHEMA_VERSIONS | TECHNICAL | Freeze/checksums схемы | TECHNICAL | 1 | Append-only governance | Нет; потеряется отдельное owner approval | REQUIRED |
| RAW_EXTRACTION_RUNS | TECHNICAL | Учёт каждой попытки EntitySet | TECHNICAL | 30–45/run | Иная гранулярность, чем errors | Нет; merge размножит run | REQUIRED |
| RAW_EXTRACTION_ERRORS | TECHNICAL | Безопасные ошибки | TECHNICAL | 0/dynamic | Несколько errors на run | Можно держать внешним audit log; merge потеряет 1:N | JUSTIFIED_OPTIONAL |
| RAW_DATA_DICTIONARY | METADATA | Копия data contract в workbook | TECHNICAL | 514 | Самодокументирование | Можно оставить только versioned CSV; данные источника не теряются | JUSTIFIED_OPTIONAL |
| RAW_ENTITYSET_MAPPING | METADATA | Копия source mappings | TECHNICAL | 38 | Самодокументирование | Можно оставить только versioned CSV; меньше self-audit | JUSTIFIED_OPTIONAL |
| RAW_PRODUCTS | CORE | Product master | Catalog_Номенклатура | 204 | Одна строка на товар | Нет; merge с variants размножит 56 product fields | REQUIRED |
| RAW_VARIANTS | CORE | Characteristic/color master | Catalog_ХарактеристикиНоменклатуры | 9 114 | Самостоятельная 1:N grain | Нет; разрушится product/variant identity | REQUIRED |
| RAW_CLASSIFICATIONS | CORE | Namespaced category nodes | Catalog_Номенклатура; Catalog_iq_Категории | ≥33 + dynamic | Узлы отдельно от links | Нет; нельзя смешивать node и relation | REQUIRED |
| RAW_PRODUCT_CLASSIFICATIONS | CORE | M:N product-category | Catalog_Номенклатура; InformationRegister_iq_КатегорииТоваров | 407 core + marketplace later | Relation grain | Нет; merge создаст дубли products/categories | REQUIRED |
| RAW_MANUFACTURERS | CORE | Referenced manufacturer lookup | Catalog_Производители | 15 | Стабильный справочник | Денормализация возможна только вне RAW; иначе теряется lookup identity | REQUIRED |
| RAW_UNIT_DEFINITIONS | CORE | Referenced units | Catalog_УпаковкиЕдиницыИзмерения | ≥3, transitive closure | Unit role | Нет; сначала нужно разрешить package/unit semantics | REQUIRED |
| RAW_PACKAGE_SETS | CORE | Referenced package set | Catalog_НаборыУпаковок | 1 | Отдельный source catalog | Можно отложить; product raw FK остаётся nullable | JUSTIFIED_OPTIONAL |
| RAW_PACKAGE_ITEMS | CORE | Package children | Catalog_УпаковкиЕдиницыИзмерения | 0 confirmed | Только future placeholder | Да, физически отложить; текущих данных не теряет | PREMATURE |
| RAW_WAREHOUSES | CORE | Warehouse lookup | Catalog_Склады | 8 | Читаемость stock keys | Нет; names повторятся во всех balances | REQUIRED |
| RAW_PRICE_TYPES | CORE | Price-type lookup | Catalog_ВидыЦен | 10 | Стабильная типизация цен | Нет; иначе name/code дублируются | REQUIRED |
| RAW_PRICE_SNAPSHOT | COMMERCIAL | Последние source price records | InformationRegister_ЦеныНоменклатуры_RecordType | 62 878 current baseline; ≤91 140 | Product+variant+type grain | Нет; grain отличается от product/variant | REQUIRED |
| RAW_STOCK_BALANCES | COMMERCIAL | Рассчитанный current balance | AccumulationRegister_СвободныеОстатки_RecordType | 72 912 full matrix | Концепт нужен, но это STAGING | Не merge; переименовать/переклассифицировать, иначе false provenance | PREMATURE |
| RAW_STOCK_TOTALS | COMMERCIAL | Сумма рассчитанных warehouse balances | RAW_STOCK_BALANCES | 9 114 | Только удобство контроля | Да; считать validation/consumer-side, raw source не теряется | DUPLICATIVE |
| RAW_BARCODES | COMMERCIAL | Barcode relations | InformationRegister_ШтрихкодыНоменклатуры | 14 295 | M:N relation grain | Нет; variants будут дублироваться | JUSTIFIED_OPTIONAL |
| RAW_SUPPLIER_ITEMS | COMMERCIAL | Supplier aliases/articles | Catalog_НоменклатураПоставщиков | 333 | 1:N supplier grain | Нет; product rows размножатся | JUSTIFIED_OPTIONAL |
| RAW_VARIANT_IMAGE_LINKS | MEDIA | Точная variant→image/color связь | Catalog_iq_ИзображенияХарактеристик | 6 173 | Логическая связь не равна file | Нет; потеряется exact color-photo chain | REQUIRED |
| RAW_COLOR_SCHEMES | MEDIA | Официальные source colors | Catalog_iq_ЦветоваяСхема | 886 | Referenced lookup | Нет; HEX/RGB будет многократно повторяться | REQUIRED |
| RAW_COLOR_PALETTES | MEDIA | Referenced palettes | Catalog_iq_ЦветоваяПалитра | 20 observed | Дополнительный lookup | Можно отложить; variant photo identity сохраняется | JUSTIFIED_OPTIONAL |
| RAW_PRODUCT_FILES | MEDIA | Product-level files | Catalog_НоменклатураПрисоединенныеФайлы | 445 | Owner semantics отличаются от variant | Нет; нельзя смешивать owner types | JUSTIFIED_OPTIONAL |
| RAW_VARIANT_FILES | MEDIA | Exact variant attached-file metadata | Catalog_iq_ИзображенияХарактеристикПрисоединенныеФайлы | ≤6 170 unique refs | Обязательное звено фотоцепочки | Нет; link/file identities различны | REQUIRED |
| RAW_BINARY_STORAGE_METADATA | MEDIA | Composite storage metadata, без Base64 | InformationRegister_ДвоичныеДанныеФайлов | ≤6 615 refs before dedup | Полиморфный file+type key | Можно загружать on-demand; без него bulk hash недоступен | JUSTIFIED_OPTIONAL |
| RAW_DESCRIPTIONS | CONTENT | Direct/plain/HTML source content | Catalog_Номенклатура; Catalog_iq_ОписаниеТовара | 316 potential / 309 non-empty | Разные content types | Нет; один текст перезапишет другой | REQUIRED |
| RAW_ATTRIBUTE_DEFINITIONS | CONTENT | Web-filter definitions | Catalog_iq_Фильтры | ≤503 before dedup | EAV dictionary | Нет; values потеряют смысл | REQUIRED |
| RAW_ATTRIBUTE_VALUES | CONTENT | Product web-filter values | InformationRegister_iq_ФильтрыТоваровИнтернетМагазина | 7 860 | Variable EAV facts | Нет; flatten создаст sparse/unstable product schema | REQUIRED |
| RAW_MARKETPLACE_LISTINGS | MARKETPLACE | Kaspi/Ozon identities | Catalog_Kaspi_КарточкаТовара; InformationRegister_Ozon_СоответствиеТоваров | 4 910 + ≥2 408 | Platform-qualified listing grain | Нет; platform identity потеряется | JUSTIFIED_OPTIONAL |
| RAW_MARKETPLACE_CONTENT | MARKETPLACE | Marketplace source content | Catalog_Kaspi_КарточкаТовара | 4 910 | Content отделён от identity | Теоретически merge для Kaspi; создаст wide sparse future schema | JUSTIFIED_OPTIONAL |
| RAW_MARKETPLACE_IMAGES | MARKETPLACE | Listing image lines | Catalog_Kaspi_КарточкаТовара_images | 5 133 | 1:N images | Нет; несколько images на listing потеряются | JUSTIFIED_OPTIONAL |
| RAW_PRODUCT_RELATIONS | RELATIONS | Explicit source recommendations | Catalog_iq_РекомендуемыеТовары | 5 | M:N source-target grain | Нет; relation нельзя встроить в product | JUSTIFIED_OPTIONAL |

Листы, созданные преимущественно для будущего: `RAW_PACKAGE_ITEMS`. Листы, относящиеся к STAGING: `RAW_STOCK_BALANCES`, `RAW_STOCK_TOTALS`, а также отдельные derived-поля, перечисленные ниже. Чрезмерного дробления подтверждённых product/media/content сущностей не выявлено; разделение link, scheme, attached file и binary metadata обосновано.

## 5. Проверка 514 полей

### 5.1. Итоговая взаимоисключающая классификация

| Класс | Полей |
|---|---:|
| SOURCE_CONFIRMED | 220 |
| SOURCE_UNCONFIRMED | 14 |
| TECHNICAL_REQUIRED | 209 |
| DERIVED_BUT_JUSTIFIED | 17 |
| MOVE_TO_STAGING | 26 |
| MOVE_TO_IDEAL | 0 |
| DUPLICATE | 7 |
| REMOVE_OR_REVIEW | 21 |
| **Итого** | **514** |

Из 251 полей, объявленных `ORIGINAL`, 210 сопоставлены с точной metadata property, 29 требуют multi-source/expression проверки, 12 прямо имеют `UNCONFIRMED_SOURCE`. Ещё два неподтверждённых `language_code` объявлены technical placeholders, поэтому общий реестр без точного source равен 14. Metadata mismatch по имени exact property не найден.

### 5.2. Распределение по листам

Сокращения: SC — SOURCE_CONFIRMED, SU — SOURCE_UNCONFIRMED, TR — TECHNICAL_REQUIRED, DJ — DERIVED_BUT_JUSTIFIED, STG — MOVE_TO_STAGING, DUP — DUPLICATE, RR — REMOVE_OR_REVIEW.

| Лист | Всего | SC | SU | TR | DJ | STG | DUP | RR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| RAW_SOURCE_SYSTEMS | 8 | 0 | 0 | 8 | 0 | 0 | 0 | 0 |
| RAW_SCHEMA_VERSIONS | 9 | 0 | 0 | 7 | 2 | 0 | 0 | 0 |
| RAW_EXTRACTION_RUNS | 18 | 0 | 0 | 13 | 5 | 0 | 0 | 0 |
| RAW_EXTRACTION_ERRORS | 12 | 0 | 0 | 12 | 0 | 0 | 0 | 0 |
| RAW_DATA_DICTIONARY | 22 | 0 | 0 | 22 | 0 | 0 | 0 | 0 |
| RAW_ENTITYSET_MAPPING | 16 | 0 | 0 | 16 | 0 | 0 | 0 | 0 |
| RAW_PRODUCTS | 56 | 52 | 0 | 4 | 0 | 0 | 0 | 0 |
| RAW_VARIANTS | 15 | 9 | 0 | 4 | 0 | 2 | 0 | 0 |
| RAW_CLASSIFICATIONS | 17 | 10 | 1 | 6 | 0 | 0 | 0 | 0 |
| RAW_PRODUCT_CLASSIFICATIONS | 9 | 2 | 1 | 6 | 0 | 0 | 0 | 0 |
| RAW_MANUFACTURERS | 8 | 4 | 0 | 4 | 0 | 0 | 0 | 0 |
| RAW_UNIT_DEFINITIONS | 16 | 12 | 0 | 4 | 0 | 0 | 0 | 0 |
| RAW_PACKAGE_SETS | 10 | 6 | 0 | 4 | 0 | 0 | 0 | 0 |
| RAW_PACKAGE_ITEMS | 20 | 0 | 0 | 0 | 0 | 0 | 0 | 20 |
| RAW_WAREHOUSES | 8 | 4 | 0 | 4 | 0 | 0 | 0 | 0 |
| RAW_PRICE_TYPES | 8 | 3 | 1 | 4 | 0 | 0 | 0 | 0 |
| RAW_PRICE_SNAPSHOT | 15 | 8 | 0 | 6 | 1 | 0 | 0 | 0 |
| RAW_STOCK_BALANCES | 13 | 0 | 0 | 0 | 0 | 13 | 0 | 0 |
| RAW_STOCK_TOTALS | 10 | 0 | 0 | 0 | 0 | 10 | 0 | 0 |
| RAW_BARCODES | 9 | 4 | 0 | 5 | 0 | 0 | 0 | 0 |
| RAW_SUPPLIER_ITEMS | 14 | 10 | 0 | 4 | 0 | 0 | 0 | 0 |
| RAW_VARIANT_IMAGE_LINKS | 14 | 10 | 0 | 4 | 0 | 0 | 0 | 0 |
| RAW_COLOR_SCHEMES | 13 | 9 | 0 | 4 | 0 | 0 | 0 | 0 |
| RAW_COLOR_PALETTES | 12 | 8 | 0 | 4 | 0 | 0 | 0 | 0 |
| RAW_PRODUCT_FILES | 21 | 10 | 1 | 6 | 1 | 0 | 3 | 0 |
| RAW_VARIANT_FILES | 21 | 10 | 1 | 6 | 0 | 0 | 3 | 1 |
| RAW_BINARY_STORAGE_METADATA | 15 | 3 | 0 | 7 | 5 | 0 | 0 | 0 |
| RAW_DESCRIPTIONS | 15 | 3 | 2 | 8 | 2 | 0 | 0 | 0 |
| RAW_ATTRIBUTE_DEFINITIONS | 16 | 11 | 1 | 4 | 0 | 0 | 0 | 0 |
| RAW_ATTRIBUTE_VALUES | 13 | 3 | 1 | 9 | 0 | 0 | 0 | 0 |
| RAW_MARKETPLACE_LISTINGS | 20 | 14 | 0 | 6 | 0 | 0 | 0 | 0 |
| RAW_MARKETPLACE_CONTENT | 15 | 8 | 1 | 6 | 0 | 0 | 0 | 0 |
| RAW_MARKETPLACE_IMAGES | 14 | 4 | 1 | 6 | 1 | 1 | 1 | 0 |
| RAW_PRODUCT_RELATIONS | 12 | 3 | 3 | 6 | 0 | 0 | 0 | 0 |
| **Итого** | **514** | **220** | **14** | **209** | **17** | **26** | **7** | **21** |

### 5.3. Полный список полей без точного подтверждённого источника

| Лист | Поле | Nullable | Решение до approval |
|---|---|---|---|
| RAW_CLASSIFICATIONS | full_path_raw | YES | оставить null или удалить из v1 header |
| RAW_PRODUCT_CLASSIFICATIONS | is_primary_raw | YES | оставить null или удалить |
| RAW_PRICE_TYPES | currency_id_raw | YES | оставить null или удалить |
| RAW_PRODUCT_FILES | file_role_raw | YES | оставить null |
| RAW_VARIANT_FILES | file_role_raw | YES | оставить null |
| RAW_DESCRIPTIONS | language_code | **NO** | либо `TECHNICAL=und`, либо nullable source field; не смешивать |
| RAW_DESCRIPTIONS | active_status_raw | YES | оставить null или удалить |
| RAW_ATTRIBUTE_DEFINITIONS | unit_raw | YES | оставить null или удалить |
| RAW_ATTRIBUTE_VALUES | value_type_raw | YES | заменить metadata-derived type либо оставить null |
| RAW_MARKETPLACE_CONTENT | language_code | **NO** | либо `TECHNICAL=und`, либо nullable source field; не смешивать |
| RAW_MARKETPLACE_IMAGES | image_reference_raw | YES | оставить null или удалить |
| RAW_PRODUCT_RELATIONS | source_variant_id | YES | оставить null |
| RAW_PRODUCT_RELATIONS | target_variant_id | YES | оставить null |
| RAW_PRODUCT_RELATIONS | relation_value_raw | YES | оставить null |

### 5.4. Восемь source/type расхождений

| Поле | Contract type | Metadata type | Требуемая коррекция |
|---|---|---|---|
| RAW_PRODUCTS.units_per_package_raw | decimal | Edm.String | хранить raw text; numeric parse только в STAGING |
| RAW_PRODUCTS.color_count_raw | integer | Edm.String | хранить raw text; numeric parse только в STAGING |
| RAW_VARIANTS.product_id ← Owner | uuid | Edm.String | проверять `Owner_Type`, сохранить owner raw; UUID — детерминированная typed link |
| RAW_PACKAGE_ITEMS.package_set_id ← Owner | uuid | Edm.String | то же; лист сначала подтвердить данными |
| RAW_ATTRIBUTE_DEFINITIONS.scope_raw | text | Edm.Guid | объявить logical UUID/text-safe GUID последовательно |
| RAW_ATTRIBUTE_VALUES.value_raw | text | Edm.Boolean | сохранить source boolean либо явно документированную lexical serialization |
| RAW_MARKETPLACE_CONTENT.listing_id | text FK | Edm.Guid | строить тот же platform-qualified key, сохранив Ref_Key отдельно |
| RAW_MARKETPLACE_IMAGES.listing_id | text FK | Edm.Guid | строить тот же platform-qualified key, сохранив Ref_Key отдельно |

### 5.5. Поля, требующие переноса/удаления

- **MOVE_TO_STAGING (26):** все 13 полей `RAW_STOCK_BALANCES`; все 10 полей `RAW_STOCK_TOTALS`; `RAW_VARIANTS.color_code_derived`; `RAW_VARIANTS.color_name_derived`; `RAW_MARKETPLACE_IMAGES.is_primary_derived`.
- **DUPLICATE (7):** `mime_type_derived`, `display_order_derived`, `content_hash_sha256` в обоих file sheets; `RAW_MARKETPLACE_IMAGES.position_derived`.
- **REMOVE_OR_REVIEW (21):** 20 полей пустого `RAW_PACKAGE_ITEMS`; `RAW_VARIANT_FILES.is_primary_derived`.
- **DERIVED_BUT_JUSTIFIED (17):** schema checksums (2), extraction counters/checksum (5), price selection rule (1), binary verification metadata (5), description length/hash (2), exact product primary-image marker (1), safe URL hash (1).

### 5.6. Исходные значения, nullable и deletion

AI/IDEAL-полей не найдено: нет softness, warmth, recommended projects, AI confidence или sales description. Исходные content/HTML сохраняются. Derived-поля, признанные допустимыми, имеют однозначный путь к source либо служат checksum/control.

Для 38 полей контракт жёстче metadata по nullable. Поскольку 1С OData часто публикует business fields как nullable, это не автоматическая ошибка, но каждый `nullable=NO` должен быть подтверждён test extraction. Особенно недопустимо подменять null на zero GUID без явного semantics.

Deletion rule необходимо задавать на уровне source row/entity, а не механически повторять на каждом field. Technical, metadata, snapshot и aggregate records должны иметь отдельные retention/replace rules; source `DeletionMark` сохраняется только там, где он реально опубликован.

## 6. Граница RAW / STAGING / IDEAL

| Объект | Фактическая природа | Red-team решение |
|---|---|---|
| Direct OData fields | Source facts | RAW |
| Namespace-qualified IDs | Детерминированные технические ключи с сохранением source ID | RAW допустимо |
| Checksums, counts, run IDs | Контроль/аудит | RAW technical допустимо |
| RAW_PRICE_SNAPSHOT | Выбор одной последней реальной source record | Допустимо как source-close snapshot при сохранении `Period`, source record и cutoff |
| Parsed color code/name | Нормализация строки характеристики | STAGING |
| Stock balance | Агрегация многих movements | STAGING/current snapshot |
| Explicit zero stock rows | Синтез полной матрицы | STAGING |
| Stock total | Повторная агрегация balances | Validation/consumer projection; не отдельный RAW fact |
| MIME/hash/magic-byte result | Техническая проверка binary | Хранить один раз в binary metadata |
| Marketplace primary image | Вывод из LineNumber | STAGING |
| AI/экспертные свойства | Не обнаружены | IDEAL, вне v1 |

Главная граница соблюдена для product, variants, descriptions, classifications, web filters и media source entities. Нарушение локализовано и исправимо: stock calculations и три normalizing fields не должны называться RAW. Это не требует новой архитектуры: import plan уже содержит staging до загрузки.

## 7. Проверка 38 EntitySet mappings

### 7.1. Сводка

| Red-team статус | Mappings |
|---|---:|
| CONFIRMED_IMPLEMENTABLE | 23 |
| TECHNICAL_CONTRACT_MAPPING | 6 |
| TEST_EXTRACTION_REQUIRED | 5 |
| PREMATURE_EMPTY | 1 |
| REVISE_RAW_BOUNDARY | 1 |
| MOVE_TO_STAGING_OR_REMOVE | 1 |
| NEEDS_REFERENCED_PRODUCT_CLOSURE | 1 |
| **Итого** | **38** |

Все 26 предметных EntitySet существуют в сохранённой опубликованной metadata. `TECHNICAL` и `RAW_STOCK_BALANCES` в mapping file не являются OData EntitySet и считаются соответственно contract-generated и derived input.

### 7.2. Все mappings

| # | Target | Source / role | Grain / key | Scope | Contract status | Red-team статус |
|---:|---|---|---|---|---|---|
| 1 | RAW_PRODUCTS | Catalog_Номенклатура / primary | product / Ref_Key | active yarn branch | VALIDATED | CONFIRMED_IMPLEMENTABLE |
| 2 | RAW_VARIANTS | Catalog_ХарактеристикиНоменклатуры / primary | characteristic / Ref_Key + Owner | 9 114 GUIDs | VALIDATED | CONFIRMED_IMPLEMENTABLE; Owner typing correction |
| 3 | RAW_CLASSIFICATIONS | Catalog_Номенклатура / 1C groups | folder / Ref_Key | yarn ancestors | CONFIRMED | CONFIRMED_IMPLEMENTABLE |
| 4 | RAW_CLASSIFICATIONS | Catalog_iq_Категории / web | category / Ref_Key | referenced by yarn | VALIDATED | CONFIRMED_IMPLEMENTABLE |
| 5 | RAW_PRODUCT_CLASSIFICATIONS | Catalog_Номенклатура / parent link | product-parent | 204 products | VALIDATED | CONFIRMED_IMPLEMENTABLE |
| 6 | RAW_PRODUCT_CLASSIFICATIONS | InformationRegister_iq_КатегорииТоваров / web link | product-category | 204 products | VALIDATED_WITH_ONE_MISSING | CONFIRMED_IMPLEMENTABLE; missing counted |
| 7 | RAW_MANUFACTURERS | Catalog_Производители / lookup | manufacturer / Ref_Key | referenced only | VALIDATED | CONFIRMED_IMPLEMENTABLE |
| 8 | RAW_UNIT_DEFINITIONS | Catalog_УпаковкиЕдиницыИзмерения / lookup | unit / Ref_Key | transitive referenced | CONFIRMED | CONFIRMED_IMPLEMENTABLE; package semantics test |
| 9 | RAW_PACKAGE_SETS | Catalog_НаборыУпаковок / lookup | set / Ref_Key | referenced | VALIDATED | CONFIRMED_IMPLEMENTABLE |
| 10 | RAW_PACKAGE_ITEMS | Catalog_УпаковкиЕдиницыИзмерения / children | Owner=package set | referenced owner | VALIDATED_EMPTY | PREMATURE_EMPTY |
| 11 | RAW_WAREHOUSES | Catalog_Склады / lookup | warehouse / Ref_Key | stock referenced | CONFIRMED | CONFIRMED_IMPLEMENTABLE |
| 12 | RAW_PRICE_TYPES | Catalog_ВидыЦен / lookup | type / Ref_Key | price referenced | VALIDATED | CONFIRMED_IMPLEMENTABLE |
| 13 | RAW_PRICE_SNAPSHOT | InformationRegister_ЦеныНоменклатуры_RecordType | product+variant+type / latest Period | 204 products | RULE_CONFIRMED_COUNT_PENDING | TEST_EXTRACTION_REQUIRED |
| 14 | RAW_STOCK_BALANCES | AccumulationRegister_СвободныеОстатки_RecordType | product+variant+warehouse / signed sum | 204 products | RULE_CONFIRMED_COUNT_PENDING | REVISE_RAW_BOUNDARY |
| 15 | RAW_STOCK_TOTALS | RAW_STOCK_BALANCES / derived control | variant / sum warehouses | all variants | RULE_CONFIRMED | MOVE_TO_STAGING_OR_REMOVE |
| 16 | RAW_BARCODES | InformationRegister_ШтрихкодыНоменклатуры | barcode relation | 204 products | VALIDATED | CONFIRMED_IMPLEMENTABLE; package FK correction |
| 17 | RAW_SUPPLIER_ITEMS | Catalog_НоменклатураПоставщиков | supplier record / Ref_Key | 204 products | VALIDATED | CONFIRMED_IMPLEMENTABLE; package FK correction |
| 18 | RAW_VARIANT_IMAGE_LINKS | Catalog_iq_ИзображенияХарактеристик | link / Ref_Key | 204 products | VALIDATED | CONFIRMED_IMPLEMENTABLE |
| 19 | RAW_COLOR_SCHEMES | Catalog_iq_ЦветоваяСхема | scheme / Ref_Key | referenced | VALIDATED | CONFIRMED_IMPLEMENTABLE |
| 20 | RAW_COLOR_PALETTES | Catalog_iq_ЦветоваяПалитра | palette / Ref_Key | referenced | COUNT_PENDING | TEST_EXTRACTION_REQUIRED |
| 21 | RAW_PRODUCT_FILES | Catalog_НоменклатураПрисоединенныеФайлы | product file / Ref_Key | 203 linked products | VALIDATED | CONFIRMED_IMPLEMENTABLE |
| 22 | RAW_VARIANT_FILES | Catalog_iq_ИзображенияХарактеристикПрисоединенныеФайлы | variant file / Ref_Key | 6 170 nonzero keys | COUNT_PENDING | TEST_EXTRACTION_REQUIRED |
| 23 | RAW_BINARY_STORAGE_METADATA | InformationRegister_ДвоичныеДанныеФайлов | file+type composite key | referenced files only | MECHANISM_VALIDATED_COUNT_PENDING | TEST_EXTRACTION_REQUIRED |
| 24 | RAW_DESCRIPTIONS | Catalog_Номенклатура / direct | product + content type | 204 products | VALIDATED | CONFIRMED_IMPLEMENTABLE |
| 25 | RAW_DESCRIPTIONS | Catalog_iq_ОписаниеТовара / website | owner + plain/HTML | 204 products | VALIDATED | CONFIRMED_IMPLEMENTABLE |
| 26 | RAW_ATTRIBUTE_DEFINITIONS | Catalog_iq_Фильтры | definition / Ref_Key | values + parents | VALIDATED_REFERENCES | CONFIRMED_IMPLEMENTABLE |
| 27 | RAW_ATTRIBUTE_VALUES | InformationRegister_iq_ФильтрыТоваровИнтернетМагазина | product-filter record | 204 products | VALIDATED | CONFIRMED_IMPLEMENTABLE; value type correction |
| 28 | RAW_MARKETPLACE_LISTINGS | Catalog_Kaspi_КарточкаТовара | platform+Ref_Key | 204 products | VALIDATED | CONFIRMED_IMPLEMENTABLE; qualified FK correction |
| 29 | RAW_MARKETPLACE_CONTENT | Catalog_Kaspi_КарточкаТовара | listing content | same cards | VALIDATED | CONFIRMED_IMPLEMENTABLE; qualified FK correction |
| 30 | RAW_MARKETPLACE_IMAGES | Catalog_Kaspi_КарточкаТовара_images | Ref_Key+LineNumber | 4 910 cards | VALIDATED | CONFIRMED_IMPLEMENTABLE; qualified FK correction |
| 31 | RAW_MARKETPLACE_LISTINGS | InformationRegister_Ozon_СоответствиеТоваров | composite register key | small batches | PARTIAL_QUERY_LENGTH_LIMIT | TEST_EXTRACTION_REQUIRED |
| 32 | RAW_PRODUCT_RELATIONS | Catalog_iq_РекомендуемыеТовары | owner-target | 204 products | VALIDATED | NEEDS_REFERENCED_PRODUCT_CLOSURE |
| 33 | RAW_SOURCE_SYSTEMS | TECHNICAL | source_system_id | contract | CONTRACT | TECHNICAL_CONTRACT_MAPPING |
| 34 | RAW_SCHEMA_VERSIONS | TECHNICAL | schema_version_id | contract | CONTRACT | TECHNICAL_CONTRACT_MAPPING |
| 35 | RAW_EXTRACTION_RUNS | TECHNICAL | run_id | every extraction | CONTRACT | TECHNICAL_CONTRACT_MAPPING |
| 36 | RAW_EXTRACTION_ERRORS | TECHNICAL | error_id | errors only | CONTRACT | TECHNICAL_CONTRACT_MAPPING |
| 37 | RAW_DATA_DICTIONARY | TECHNICAL | sheet+field | contract | CONTRACT | TECHNICAL_CONTRACT_MAPPING; PK fix |
| 38 | RAW_ENTITYSET_MAPPING | TECHNICAL | target+entity+role | contract | CONTRACT | TECHNICAL_CONTRACT_MAPPING; PK fix |

### 7.3. Критические цепочки

| Цепочка | Статус | Условие/дефект |
|---|---|---|
| Product → Characteristic | Подтверждена условно | `Owner` + `Owner_Type` должны типизироваться вместе; не терять raw owner |
| Characteristic → Variant Image Link | Подтверждена | Exact `product_id` + `variant_id`; 6 173 links |
| Variant Image Link → Color Scheme | Подтверждена | `ЦветоваяСхема_Key`; referenced closure обязателен |
| Image Link → Attached File | Подтверждена, count pending | `image_Key` → file `Ref_Key`; все nonzero refs должны разрешиться |
| Attached File → Binary Storage | Механизм подтверждён | Composite (`Файл`, `Файл_Type`); проверять пару, Base64 не писать в Sheets |
| Product/Characteristic → Barcode | Подтверждена | Product/variant links корректны; package target требует уточнения |
| Product → Web Filters | Подтверждена | Definitions + values; source `Значение` сейчас Boolean |
| Product/Variant → Prices | Правило подтверждено | Нужны full count и корректная модель product-level price |
| Product/Variant/Warehouse → Stock | Source подтверждён, target слой неверен | Aggregate не является raw source row |
| Product/Variant → Kaspi/Ozon | Kaspi подтверждён; Ozon partial | Qualified listing key должен быть одинаковым во всех трёх sheets |

Противоречивой загрузки одной source record в несколько листов нет там, где role явно различен (например Kaspi listing/content или description plain/HTML). Дубли становятся неконтролируемыми только при неверном platform key и при повторном хранении file hash/MIME/order.

## 8. Цены и остатки

### 8.1. Модель контракта

- Цены: current snapshot, выбранная последняя source record на cutoff; не полная история.
- Остатки: рассчитанный current balance на cutoff; это STAGING snapshot, не RAW movement history.
- Extraction runs: append-only audit history.
- Полная price/movement history: исключена.

### 8.2. Первая загрузка

| Набор | Фактический/ожидаемый объём |
|---|---:|
| Current non-empty price combinations в существующем RAW | **62 878 rows** |
| Contract price upper envelope | 91 140 rows |
| Full stock matrix: 9 114 variants × 8 warehouses | **72 912 rows** |
| Из них nonzero | 4 127 |
| Из них explicit/synthetic zero | 68 785 |
| Variants с total zero | 7 372 |
| Stock totals | 9 114 rows |
| Stock rows + totals | **82 026 rows** |

62 878 — полезный независимый baseline из CURRENT RAW, но acceptance count должен быть зафиксирован новой read-only extraction на едином cutoff.

### 8.3. Что произойдёт при ежедневном append

| Период | Price rows / cells (15 cols) | Balance rows / cells (13 cols) | Total rows / cells (10 cols) | Только эти три набора, cells |
|---|---:|---:|---:|---:|
| 30 дней | 1 886 340 / 28 295 100 | 2 187 360 / 28 435 680 | 273 420 / 2 734 200 | **59 464 980** |
| 365 дней | 22 950 470 / 344 257 050 | 26 612 880 / 345 967 440 | 3 326 610 / 33 266 100 | **723 490 590** |

Эта история **не входит** в оценку 3 452 888/3 454 844. Уже первый месяц превысит официальный лимит одного spreadsheet.

### 8.4. Рекомендация владельцу

Для MVP хранить только одно актуальное состояние на зафиксированный cutoff плюс append-only extraction log. Не накапливать ежедневные price/stock partitions в том же Google Sheets. Если история станет бизнес-требованием, она должна оставаться во внешнем source/audit storage или БД; это отдельное решение, не часть RAW Product Knowledge v1.

## 9. Проверка 169 validations

### 9.1. Классификация

| Измерение | Класс | Количество |
|---|---|---:|
| Автоматизация | Реально автоматизируется | 163 |
| Автоматизация | Невозможно как написано | 6 |
| Результат | Automatic blocking | 163 |
| Результат | Blocking, но impossible | 6 |
| Результат | Automatic warning | 0 |
| Результат | Report-only | 0 |
| Ручная работа внутри matrix | Manual | 0 |
| Периодичность | One-time migration/schema | 13 |
| Периодичность | Every import | 156 |
| Дублирование | Точные дубли в одном sheet/rule/evidence | 0 |

Все 169 проверок блокируют импорт. 62 строки используют повторяемые шаблоны PK/required/idempotency/provenance на разных листах; это не дубли, а независимые sheet-level проверки. Owner approval — ручной governance gate вне validation matrix.

### 9.2. Severity и типы

| Severity | Количество |
|---|---:|
| P0 | 79 |
| P1 | 90 |

| Check type | Количество |
|---|---:|
| PK_UNIQUENESS | 34 |
| REQUIRED_KEYS | 34 |
| IDEMPOTENCY | 34 |
| PROVENANCE | 28 |
| GUID_FORMAT | 24 |
| CONTROL_COUNT | 3 |
| SOURCE_PRESERVATION | 3 |
| SECURITY | 2 |
| AGGREGATION | 2 |
| RELATION_INTEGRITY | 1 |
| RECONCILIATION | 1 |
| TEXT_PRESERVATION | 1 |
| CONTROL_ACCOUNTING | 1 |
| CHECKSUM | 1 |

### 9.3. Исправление validation gate

До реализации нужно:

1. исправить два composite PK и evidence fields двух controls;
2. убрать source-row provenance с aggregates, заменив его input-set checksum/count/cutoff в STAGING;
3. после этого пересчитать matrix;
4. отделить true blockers (schema, PK/FK, secrets, wrong photo relation, source mutation) от warning/report-only counts (optional missing relations, pending optional coverage);
5. оставить P0/P1 blocking только там, где stop действительно необходим.

## 10. Практическая оценка Google Sheets

### 10.1. Лимиты и рабочие пороги

| Уровень | Оценка |
|---|---|
| Официальный технический предел | 10 000 000 cells/spreadsheet; при конвертации cells длиннее 50 000 characters удаляются — [Google Drive Help](https://support.google.com/drive/answer/37603?hl=en) |
| API constraints | рекомендованный payload ≤2 MB; 300 read и 300 write requests/min/project, 60/min/user; request timeout 180 sec; exponential backoff — [Google Sheets API limits](https://developers.google.com/workspace/sheets/api/limits) |
| Практически безопасная зона проекта | около 2–3 млн фактически используемых cells для регулярно читаемого/обновляемого файла; это engineering threshold, не лимит Google |
| Рекомендуемый рабочий объём | Phase 1 ≤2 млн cells; полный frozen/read-mostly v1 допускается до текущего ceiling около 3,5 млн при условиях ниже |

### 10.2. Прямой ответ

**Подходит ли Google Sheets для текущего RAW COMPLETE на 204 товара? — YES, WITH CONDITIONS.**

Условия:

1. Только один current/frozen snapshot; price/stock history не append в этот workbook.
2. Сначала Phase 1 и фактический used-range projection; stop/review уже при прогнозе выше 3,5 млн, а не 7 млн.
3. Values payload делить по фактическому JSON-size, целиться ниже 2 MB/request; использовать batch operations и exponential backoff.
4. Не использовать workbook-wide formulas, volatile formulas, full-column formatting или cross-sheet calculations по крупным sheets.
5. Создавать/resize только фактический used range; не резервировать сотни тысяч пустых строк.
6. Сортировку, joins, checksum и validation выполнять вне Sheets; в файле оставлять values и ограниченные filters.
7. Полный refresh делать partition/upsert-стратегией с checksum, а не cell-by-cell updates.
8. Source HTML проверять на 50 000 characters до записи; текущий известный максимум 4 590 безопасен.
9. Protect headers/source sheets и ограничить человеческое редактирование.
10. Фиксировать duration, requests, retries и payload size в extraction report; timeout/retry не должен создавать duplicate rows.

При этих условиях один read-mostly workbook реализуем. Для частого интерактивного анализа 3,45 млн cells уже не является комфортным объёмом: открытие, filters и sorts могут заметно замедлиться, даже не достигая hard limit.

## 11. Классификация открытых вопросов

| Вопрос | Класс | Конкретная проверка и критерий |
|---|---|---|
| Ozon final count | PHASE_2_BLOCKER | пройти весь scoped product list малыми batches; каждый batch 2xx; 0 пропущенных keys/404.15; unique composite count и повтор на том же cutoff совпадают |
| Variant attached-file count | PHASE_1_BLOCKER | dedup всех 6 170 nonzero `image_Key`; каждый key разрешается ровно в одну file row либо missing явно блокирует exact photo relation |
| Palette count | RESOLVED_BY_TEST_EXTRACTION | dedup referenced palette GUIDs; все nonzero palette refs разрешены; expected=extracted=validated |
| Price snapshot row count | PHASE_1_BLOCKER | full scoped extraction на одном cutoff; latest key unique; baseline 62 878 объяснён/reconciled; 0 unaccounted rejects |
| File roles | NON_BLOCKING | неизвестные roles остаются null; primary только по подтверждённой direct link |
| Language | NON_BLOCKING | выбрать один contract semantics: technical `und` либо nullable source; не выполнять language inference |
| Marketplace category paths | NON_BLOCKING | сохранять raw platform IDs; path не строить без lookup source |
| Package items | NON_BLOCKING | физический лист отложить; сначала доказать тип `Упаковка_Key` и referenced closure |
| Binary metadata coverage | NON_BLOCKING | on-demand composite-key verification допустима; Base64 не массово загружать и не писать в Sheets |
| Owner approval | BLOCKER | возможно только после исправления критических пунктов и повторного red-team pass |

## 12. Рекомендуемая очередь реализации

### Phase 0 — обязательная correction/re-audit

Исправить только документы контракта по разделу 13, обновить checksums/counts и повторить статический аудит. До успешного результата Google Sheets не создавать.

### Phase 1A — минимальная доказательная выгрузка

Три товара и все их варианты:

- один товар с несколькими цветами, color scheme, exact photo link и binary metadata (включая Puffy как уже проверенный кейс);
- один товар без variant photo;
- один товар с нулевым total stock;
- среди набора должны присутствовать price, description/HTML, web filters, leading-zero color code и хотя бы одна nullable optional relation.

Минимальные sheets/сущности: technical run/schema/source, products, variants, classifications/links, manufacturers, units, warehouses, price types, price snapshot, исправленный current stock staging output, image links, color schemes, variant files, descriptions, attribute definitions/values. Проверяются PK/FK, platform/owner typing, exact photo chain, source preservation и idempotent rerun.

### Phase 1B — полное обязательное ядро

После успешного test report: 204 products, 9 114 variants и все REQUIRED источники. Структуру ключей после Phase 1A менять нельзя; разрешены только новые rows/runs.

### Phase 2 — расширенные источники

Barcodes, supplier items, product files, palettes, binary coverage, product relations, Kaspi/Ozon и дополнительные classifications. Ozon загружается только малыми batches после закрытия PHASE_2_BLOCKER.

Все утверждённые headers можно создать в начале после correction. `RAW_PACKAGE_ITEMS` не следует физически создавать лишь «для доказательства пустоты»; факт нулевого extraction фиксируется в run/report. Optional sheets могут существовать пустыми, если их source и schema уже подтверждены. Поэтапность не нарушит keys при условии namespace-qualified IDs, referenced closure и неизменного schema version.

## 13. Точный перечень требуемых изменений контракта

Изменения ниже **не выполнены этим аудитом**.

1. В Data Dictionary сделать PK `RAW_DATA_DICTIONARY` составным: `(sheet_name, field_name)`; отметить обе части и исправить validation/evidence.
2. Сделать PK `RAW_ENTITYSET_MAPPING` составным: `(target_sheet, source_entityset, source_role)`; исправить validation/evidence.
3. Переклассифицировать/переименовать `RAW_STOCK_BALANCES` в существующий STAGING current snapshot; убрать требование одного `source_record_id`, использовать cutoff + aggregation rule + input count + canonical input checksum.
4. Убрать физический `RAW_STOCK_TOTALS` из RAW либо сделать его validation output, не самостоятельный source table.
5. Перенести `color_code_derived`, `color_name_derived` и marketplace `is_primary_derived` в STAGING; source descriptions/LineNumber оставить без изменения.
6. Отложить `RAW_PACKAGE_ITEMS` до появления подтверждённых child rows. Для четырёх `Упаковка_Key` выполнить type/reference test и направить FK на реально соответствующий lookup, не на пустой sheet по предположению.
7. Во всех marketplace child sheets формировать тот же `(platform, source_listing_id)` technical key, что и в `RAW_MARKETPLACE_LISTINGS`, сохраняя raw `Ref_Key` отдельно.
8. Исправить category references: FK должен включать classification namespace и вести на `classification_id`, а не на неключевой `source_category_id`.
9. Удалить hash как FK из product/variant file sheets; связывать binary metadata по `(file_id, file_type_raw)`. MIME/hash/order хранить в одном каноническом месте.
10. Исправить восемь type mismatches из раздела 5.4 и сохранить raw lexical/source values рядом с любой типизацией.
11. Для product-level prices сделать `variant_id` nullable либо отдельную явную scope semantics; zero GUID не считать валидным FK.
12. Для product relations извлечь minimal referenced-product closure или определить external target identity; не создавать orphan на 204-row yarn scope.
13. Для binary storage валидировать polymorphic pair `(file_id, file_type_raw)` и exact allowed type; один `file_id` недостаточен.
14. Для 14 `UNCONFIRMED_SOURCE` либо удалить headers из v1, либо оставить nullable/reserved. Два `language_code` явно объявить technical `und`, а не source field.
15. Удалить/централизовать 7 duplicate derived fields и снять неподтверждённый `RAW_VARIANT_FILES.is_primary_derived`.
16. Исправить шесть impossible validation checks; затем разделить blocking и warning/report-only результаты. Пересчитать 169-check matrix и её checksum.
17. Заменить blanket deletion rule на entity-level source deletion и отдельные retention rules для technical/snapshot/derived records.
18. Пересчитать физические sheet/field/cell counts после corrections; текущая as-is арифметика — около 3 454 844 cells, не 3 452 888.
19. Добавить в import plan API operating contract: payload target ≤2 MB, retries/backoff, timeout handling, no formulas/full-column formatting, фактический used range и stop/review >3,5 млн cells.
20. Закрыть четыре pending counts тестами из раздела 11 и только после этого заменить readiness `A` на новый owner decision.

## Финальный вердикт

**C. REVISE BEFORE APPROVAL**

Основная модель пригодна и не требует полного redesign. Но четыре критических класса дефектов делают текущий контракт неисполняемым как написано. Следующий разрешённый шаг — correction документов контракта владельцем/архитектором и повторный audit; создание Google Sheets, ETL или переключение AI Seller пока не разрешать.
