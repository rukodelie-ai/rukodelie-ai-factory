# RAW COMPLETE v1 — ER diagram after red-team revision

Статус: **REVISED — NOT OWNER APPROVED**. Точные fields, PK и FK определяет Data Dictionary.

## Core + current commercial snapshots

```mermaid
erDiagram
  RAW_PRODUCTS ||--o{ RAW_VARIANTS : owns
  RAW_PRODUCTS }o--o| RAW_MANUFACTURERS : references
  RAW_PRODUCTS }o--o| RAW_UNIT_DEFINITIONS : uses
  RAW_PRODUCTS }o--o| RAW_PACKAGE_SETS : optional_set
  RAW_PRODUCTS ||--o{ RAW_PRODUCT_CLASSIFICATIONS : classified_as
  RAW_CLASSIFICATIONS ||--o{ RAW_PRODUCT_CLASSIFICATIONS : contains
  RAW_PRODUCTS ||--o{ RAW_CURRENT_PRICES : priced
  RAW_VARIANTS ||--o{ RAW_CURRENT_PRICES : typed_variant
  RAW_PRICE_TYPES ||--o{ RAW_CURRENT_PRICES : price_type
  RAW_PRODUCTS ||--o{ RAW_CURRENT_STOCK : stocked
  RAW_VARIANTS ||--o{ RAW_CURRENT_STOCK : stocked
  RAW_WAREHOUSES ||--o{ RAW_CURRENT_STOCK : warehouse
  RAW_PRODUCTS ||--o{ RAW_BARCODES : identifies
  RAW_VARIANTS ||--o{ RAW_BARCODES : identifies
  RAW_PRODUCTS ||--o{ RAW_SUPPLIER_ITEMS : supplier_alias
```

`RAW_PACKAGE_ITEMS` отсутствует в v1: 0 confirmed scoped rows. `Упаковка_Key` сохраняется как raw ID без выдуманного FK до type test; исходный child mapping остаётся control-only evidence в `RAW_EXTRACTION_RUNS`.

`RAW_CURRENT_STOCK` — current aggregate snapshot. У него нет fictitious single source-record FK. Lineage: cutoff + aggregation rule + source record count + canonical input checksum. Исходный total mapping сохранён как control-only lineage; `stock_total` — validation output `SUM(quantity_available)` по варианту, не физическая сущность.

## Media

```mermaid
flowchart LR
  P[RAW_PRODUCTS] --> V[RAW_VARIANTS]
  V --> L[RAW_VARIANT_IMAGE_LINKS]
  L --> C[RAW_COLOR_SCHEMES]
  C --> CP[RAW_COLOR_PALETTES]
  L --> VF[RAW_VARIANT_FILES]
  VF -->|binary_storage_id| B[RAW_BINARY_STORAGE_METADATA]
  P --> PF[RAW_PRODUCT_FILES]
  PF -->|binary_storage_id| B
```

`binary_storage_id` строится из exact pair `(file_id, file_type_raw)`. MIME/hash канонически находятся только в `RAW_BINARY_STORAGE_METADATA`. Base64/binary payload в Sheets отсутствуют.

## Content + marketplace + relations

```mermaid
erDiagram
  RAW_PRODUCTS ||--o{ RAW_DESCRIPTIONS : described_by
  RAW_PRODUCTS ||--o{ RAW_ATTRIBUTE_VALUES : has
  RAW_ATTRIBUTE_DEFINITIONS ||--o{ RAW_ATTRIBUTE_VALUES : defines
  RAW_PRODUCTS ||--o{ RAW_MARKETPLACE_LISTINGS : listed_as
  RAW_VARIANTS ||--o{ RAW_MARKETPLACE_LISTINGS : variant_listing
  RAW_CLASSIFICATIONS ||--o{ RAW_MARKETPLACE_LISTINGS : optional_category
  RAW_MARKETPLACE_LISTINGS ||--o| RAW_MARKETPLACE_CONTENT : has_content
  RAW_MARKETPLACE_LISTINGS ||--o{ RAW_MARKETPLACE_IMAGES : has_images
  RAW_PRODUCTS ||--o{ RAW_PRODUCT_RELATIONS : source
  RAW_PRODUCTS ||--o{ RAW_PRODUCT_RELATIONS : in_scope_target
```

Marketplace child FK использует один platform-qualified `listing_id`; source `Ref_Key` сохраняется отдельно. Recommendation target всегда сохраняется в `target_product_source_id`; `target_product_in_scope_id` заполняется только при membership в 204-product scope.

## Provenance

```mermaid
flowchart TD
  SS[RAW_SOURCE_SYSTEMS] --> R[RAW_EXTRACTION_RUNS]
  SV[RAW_SCHEMA_VERSIONS] --> R
  R --> E[RAW_EXTRACTION_ERRORS]
  R --> D[Direct source rows]
  R --> CS[RAW_CURRENT_STOCK]
  M[EntitySet + source role] --> D
  DD[RAW_DATA_DICTIONARY] --> D
  EM[RAW_ENTITYSET_MAPPING] --> M
  I[Movement input set checksum] --> CS
```

Direct source rows имеют `source_record_id`. Aggregated current stock имеет lineage input-set, а не ложную ссылку на одну source record.
