# RAW COMPLETE v1 — decision report

## Предложенное решение

- Отдельный Google Sheets файл; CURRENT RAW неизменяем.
- 34 физических листа, 514 описанных полей.
- Hybrid schema: прямые поля колонками, EAV только для web-фильтров.
- Record-level provenance; field-level provenance не создаётся без multi-source merge.
- Source descriptions и HTML сохраняются без очистки.
- Media разделено на link, scheme, file metadata и binary metadata; Base64 запрещён.
- Classification systems разделены namespace.
- Marketplace keys platform-qualified.
- Price/stock представлены versioned snapshots, а не полной операционной историей.
- AI Seller direct usage во всех полях: NO.

## Контрольные ориентиры

| Объект | Expected baseline | Статус |
|---|---|---|
| Товары | 204 | validated |
| Характеристики | 9,114 | validated |
| Variant image links | 6,173 | validated |
| Color schemes | 886 | validated |
| Website description records | 56 | validated |
| Product files | 445 | validated |
| Barcodes | 14,295 | validated |
| Supplier records | 333 | validated |
| Web category links | 203 | validated; 1 product missing |
| Web filter values | 7,860 | validated |
| Filter definitions | 480 + 23 parents before dedup | references validated |
| Explicit recommendations | 5 | validated |
| Kaspi cards | 4,910 | validated |
| Kaspi images | 5,133 | validated |
| Ozon mapping | >=2,408 / >=124 products | partial baseline |
| Manufacturers | 15 | validated |

## Capacity decision

Upper envelope: **3 452 888 cells**, under the official 10,000,000-cell limit. The file is feasible for 204/9,114 scope. It is not suitable for 10,000/100,000 scale, where a database becomes mandatory.

## Residual risks

- Ozon and variant-file exact counts are pending complete small-batch runs.
- Google Sheets performance may degrade below the hard limit; pre-load projection >7m is a stop.
- Source HTML/URLs require redaction checks and 50k character validation.
- Price/stock correctness depends on frozen cutoff and aggregation-rule version.
- Unprotected user edits after freeze would break checksum stability; sheet protections are required.

## Readiness

The remaining items are execution-time counts and owner governance, not unresolved architecture. No Google Sheets, ETL or production change has been performed.

## Финальное заключение

**A. «Реализационный контракт RAW COMPLETE v1 готов к утверждению владельцем».**

Это не означает, что архитектура утверждена. Реализация разрешается только отдельным решением владельца после аудита этих документов.
