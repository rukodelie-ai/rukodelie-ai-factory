# RAW COMPLETE v1 — ER diagram

Диаграмма логическая; точные поля и FK определены в Data Dictionary.

## Core + Commercial

```mermaid
erDiagram
  RAW_PRODUCTS ||--o{ RAW_VARIANTS : owns
  RAW_PRODUCTS }o--o| RAW_MANUFACTURERS : references
  RAW_PRODUCTS }o--o| RAW_UNIT_DEFINITIONS : uses
  RAW_PRODUCTS }o--o| RAW_PACKAGE_SETS : uses
  RAW_PACKAGE_SETS ||--o{ RAW_PACKAGE_ITEMS : contains
  RAW_PRODUCTS ||--o{ RAW_PRODUCT_CLASSIFICATIONS : classified_as
  RAW_CLASSIFICATIONS ||--o{ RAW_PRODUCT_CLASSIFICATIONS : contains
  RAW_PRODUCTS ||--o{ RAW_PRICE_SNAPSHOT : priced
  RAW_VARIANTS ||--o{ RAW_PRICE_SNAPSHOT : priced
  RAW_PRICE_TYPES ||--o{ RAW_PRICE_SNAPSHOT : price_type
  RAW_PRODUCTS ||--o{ RAW_STOCK_BALANCES : stocked
  RAW_VARIANTS ||--o{ RAW_STOCK_BALANCES : stocked
  RAW_WAREHOUSES ||--o{ RAW_STOCK_BALANCES : warehouse
  RAW_VARIANTS ||--|| RAW_STOCK_TOTALS : totals
  RAW_PRODUCTS ||--o{ RAW_BARCODES : identifies
  RAW_VARIANTS ||--o{ RAW_BARCODES : identifies
  RAW_PRODUCTS ||--o{ RAW_SUPPLIER_ITEMS : supplier_alias
```

## Media

```mermaid
flowchart LR
  P[RAW_PRODUCTS] --> V[RAW_VARIANTS]
  V --> L[RAW_VARIANT_IMAGE_LINKS]
  L --> C[RAW_COLOR_SCHEMES]
  C --> CP[RAW_COLOR_PALETTES]
  L --> VF[RAW_VARIANT_FILES]
  VF --> B[RAW_BINARY_STORAGE_METADATA]
  P --> PF[RAW_PRODUCT_FILES]
  PF --> B
```

Ни RAW_PRODUCT_FILES, ни RAW_VARIANT_FILES не содержат Base64. RAW_BINARY_STORAGE_METADATA хранит только факт payload, длину, MIME и hash.

## Content + Marketplace + Relations

```mermaid
erDiagram
  RAW_PRODUCTS ||--o{ RAW_DESCRIPTIONS : described_by
  RAW_PRODUCTS ||--o{ RAW_ATTRIBUTE_VALUES : has
  RAW_ATTRIBUTE_DEFINITIONS ||--o{ RAW_ATTRIBUTE_VALUES : defines
  RAW_PRODUCTS ||--o{ RAW_MARKETPLACE_LISTINGS : listed_as
  RAW_VARIANTS ||--o{ RAW_MARKETPLACE_LISTINGS : variant_listing
  RAW_MARKETPLACE_LISTINGS ||--o| RAW_MARKETPLACE_CONTENT : has_content
  RAW_MARKETPLACE_LISTINGS ||--o{ RAW_MARKETPLACE_IMAGES : has_images
  RAW_PRODUCTS ||--o{ RAW_PRODUCT_RELATIONS : source
  RAW_PRODUCTS ||--o{ RAW_PRODUCT_RELATIONS : target
```

## Provenance

```mermaid
flowchart TD
  SS[RAW_SOURCE_SYSTEMS] --> R[RAW_EXTRACTION_RUNS]
  SV[RAW_SCHEMA_VERSIONS] --> R
  R --> E[RAW_EXTRACTION_ERRORS]
  R --> D[Every subject RAW row]
  DD[RAW_DATA_DICTIONARY] --> D
  EM[RAW_ENTITYSET_MAPPING] --> D
```
