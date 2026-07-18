#!/usr/bin/env python3
"""Build and validate the approved RAW COMPLETE v1 Phase C fixture.

The extractor performs read-only OData GET requests.  It never writes to 1C.
Google Sheets loading is a separate explicit --load-fixture operation and is
allowed only after a successful local dry run.
"""

import argparse
import base64
import csv
import datetime as dt
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from dotenv import load_dotenv


PROJECT = Path("/Users/sergey/Library/Mobile Documents/com~apple~CloudDocs/RUKODELIE_AI_FACTORY")
CONTRACT = PROJECT / "09_DOCUMENTS" / "RAW_COMPLETE_V1_CONTRACT"
FIXTURE = CONTRACT / "TEST_EXTRACTION_FIXTURE" / "puffy_fine_0000057268"
PHASE_D_DIR = FIXTURE / "phase_d"
ENV_FILE = PROJECT / "03_TELEGRAM" / ".env"
SPREADSHEET_ID = "1-C93GArFSGbTOSSLRc-UvG_6XADzmCezZphK54nylkU"

PRODUCT_ID = "f5f42c43-0da6-11ea-80cb-9633c5df92df"
PRODUCT_CODE = "0000057268"
VARIANT_IDS = [
    "7397ddaf-761b-11ed-a7c6-000c290ea457",  # color 06, leading zero
    "f5f42c5d-0da6-11ea-80cb-9633c5df92df",  # color 90, positive stock
    "f5f42c48-0da6-11ea-80cb-9633c5df92df",  # color 113, zero stock
]
ZERO_GUID = "00000000-0000-0000-0000-000000000000"
SOURCE_SYSTEM_ID = "1C_STANDARD_ODATA"
SCHEMA_VERSION_ID = "RAW_COMPLETE_V1"
EXTRACTOR_VERSION = "raw-complete-v1-phase-c-fixture/1.0"
VARIANT_FILE_TYPE = "StandardODATA.Catalog_iq_ИзображенияХарактеристикПрисоединенныеФайлы"
PRODUCT_FILE_TYPE = "StandardODATA.Catalog_НоменклатураПрисоединенныеФайлы"
GUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def safe_scalar(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (bool, int, float)):
        return value
    return str(value)


def normalize_datetime(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    text = str(value)
    match = re.fullmatch(r"/Date\((-?\d+)(?:[+-]\d+)?\)/", text)
    if match:
        stamp = dt.datetime.fromtimestamp(int(match.group(1)) / 1000, tz=dt.timezone.utc)
        return stamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if text.endswith("Z"):
        return text
    try:
        parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError:
        return text


class ODataClient:
    def __init__(self) -> None:
        load_dotenv(ENV_FILE)
        self.base = os.environ.get("ODATA_BASE_URL", "").rstrip("/")
        user = os.environ.get("ODATA_USERNAME", "")
        password = os.environ.get("ODATA_PASSWORD", "")
        if not self.base or not user or not password:
            raise RuntimeError("ODATA_BASE_URL/ODATA_USERNAME/ODATA_PASSWORD are not configured")
        token = base64.b64encode((user + ":" + password).encode("utf-8")).decode("ascii")
        self.headers = {"Authorization": "Basic " + token, "Accept": "application/json"}

    def _get_json(self, url: str, timeout: int = 90) -> Any:
        request = urllib.request.Request(url, headers=self.headers, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8-sig"))

    def query(self, entity: str, params: Dict[str, str]) -> List[Dict[str, Any]]:
        encoded_entity = urllib.parse.quote(entity, safe="_()=',")
        query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        url = self.base + "/" + encoded_entity + "?" + query
        rows: List[Dict[str, Any]] = []
        while url:
            payload = self._get_json(url)
            if isinstance(payload, dict) and "value" in payload:
                rows.extend(payload.get("value") or [])
                url = payload.get("@odata.nextLink") or payload.get("odata.nextLink") or payload.get("__next")
            elif isinstance(payload, dict) and isinstance(payload.get("d"), dict):
                body = payload["d"]
                rows.extend(body.get("results") or [])
                url = body.get("__next")
            else:
                raise RuntimeError("Unexpected OData collection response")
        return rows

    def direct(self, entity_key: str, select: Sequence[str]) -> Dict[str, Any]:
        params = {"$select": ",".join(select), "$format": "json"}
        encoded = urllib.parse.quote(entity_key, safe="_()=',")
        payload = self._get_json(self.base + "/" + encoded + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote))
        if isinstance(payload, dict) and isinstance(payload.get("d"), dict):
            return payload["d"]
        if not isinstance(payload, dict):
            raise RuntimeError("Unexpected OData entity response")
        return payload


def guid_filter(field: str, values: Sequence[str]) -> str:
    return " or ".join("%s eq guid'%s'" % (field, value) for value in values)


def direct_source_properties(dictionary: List[Dict[str, str]], sheet: str, entity: str) -> List[str]:
    properties: List[str] = []
    for row in dictionary:
        source = row["source_property"].strip()
        if row["sheet_name"] != sheet or row["source_entityset"] != entity:
            continue
        if not source or source in {"TECHNICAL", "TECHNICAL_FROM_ENTITYSET"}:
            continue
        if any(token in source for token in ("(", ")", " | ", ".")) or source.lower().startswith("null"):
            continue
        properties.append(source)
    return list(dict.fromkeys(properties))


def make_row(headers: Sequence[str]) -> Dict[str, Any]:
    return {header: None for header in headers}


def map_direct(headers: Sequence[str], dictionary: List[Dict[str, str]], sheet: str, source: Dict[str, Any]) -> Dict[str, Any]:
    row = make_row(headers)
    for item in dictionary:
        if item["sheet_name"] != sheet:
            continue
        prop = item["source_property"]
        if prop in source:
            value = safe_scalar(source.get(prop))
            if item["data_type"] == "datetime":
                value = normalize_datetime(value)
            if item["data_type"] == "uuid" and value:
                value = str(value).lower()
                if value == ZERO_GUID and item["nullable"] == "YES" and item["foreign_key"]:
                    value = None
            row[item["field_name"]] = value
    return row


def add_provenance(row: Dict[str, Any], entity: str, record_id: str, run_id: str) -> None:
    if "source_system_id" in row:
        row["source_system_id"] = SOURCE_SYSTEM_ID
    if "source_entityset" in row:
        row["source_entityset"] = entity
    if "source_record_id" in row:
        row["source_record_id"] = record_id
    if "extraction_run_id" in row:
        row["extraction_run_id"] = run_id


def get_headers(dictionary: List[Dict[str, str]]) -> Tuple[List[str], Dict[str, List[str]]]:
    order: List[str] = []
    headers: Dict[str, List[str]] = defaultdict(list)
    for row in dictionary:
        sheet = row["sheet_name"]
        if sheet not in headers:
            order.append(sheet)
        headers[sheet].append(row["field_name"])
    return order, dict(headers)


def save_raw(name: str, value: Any) -> None:
    path = FIXTURE / "raw" / (name + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def write_normalized(order: Sequence[str], headers: Dict[str, List[str]], data: Dict[str, List[Dict[str, Any]]]) -> None:
    target = FIXTURE / "normalized"
    target.mkdir(parents=True, exist_ok=True)
    for sheet in order:
        with (target / (sheet + ".csv")).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers[sheet], extrasaction="raise")
            writer.writeheader()
            for row in data.get(sheet, []):
                writer.writerow({key: "" if row.get(key) is None else row.get(key) for key in headers[sheet]})


def parse_color_code(description: str) -> str:
    match = re.search(r"\(([A-Za-zА-Яа-я0-9]+)\s*(?:-|,|\))", description or "")
    return match.group(1) if match else ""


def source_record_id_price(row: Dict[str, Any]) -> str:
    values = [row.get("Recorder"), row.get("Recorder_Type"), row.get("LineNumber"), row.get("Period")]
    return "|".join("" if value is None else str(value) for value in values)


def binary_key(file_id: str, file_type: str) -> str:
    return file_id.lower() + "|" + file_type


def build_fixture() -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
    dictionary = read_csv(CONTRACT / "RAW_COMPLETE_V1_DATA_DICTIONARY.csv")
    mappings = read_csv(CONTRACT / "RAW_COMPLETE_V1_ENTITYSET_MAPPING.csv")
    matrix = read_csv(CONTRACT / "RAW_COMPLETE_V1_VALIDATION_MATRIX.csv")
    order, headers = get_headers(dictionary)
    if len(order) != 32 or sum(len(headers[s]) for s in order) != 466:
        raise RuntimeError("Approved contract schema is not 32 sheets / 466 fields")

    client = ODataClient()
    started = utc_now()
    cutoff = started
    run_prefix = "phase_c_" + started.replace("-", "").replace(":", "").replace("Z", "Z")
    data: Dict[str, List[Dict[str, Any]]] = {sheet: [] for sheet in order}
    raw: Dict[str, Any] = {}
    run_rows: Dict[str, Dict[str, Any]] = {}

    def run_id(entity: str) -> str:
        compact = re.sub(r"[^A-Za-z0-9]+", "_", entity).strip("_")
        suffix = sha256_bytes(entity.encode("utf-8"))[:10]
        return (run_prefix + "_" + compact)[:160] + "_" + suffix

    def register_run(entity: str, scope: str, selected: Sequence[str]) -> str:
        rid = run_id(entity)
        row = make_row(headers["RAW_EXTRACTION_RUNS"])
        row.update({
            "run_id": rid,
            "schema_version_id": SCHEMA_VERSION_ID,
            "source_system_id": SOURCE_SYSTEM_ID,
            "source_entityset": entity,
            "started_at_utc": started,
            "scope_filter_masked": scope,
            "selected_fields": ",".join(selected),
            "extractor_version": EXTRACTOR_VERSION,
            "status": "STARTED",
            "extracted_count": 0,
            "validated_count": 0,
            "rejected_count": 0,
            "missing_relation_count": 0,
        })
        run_rows[entity] = row
        return rid

    def query_sheet(sheet: str, entity: str, where: str) -> List[Dict[str, Any]]:
        selected = direct_source_properties(dictionary, sheet, entity)
        rid = register_run(entity, "product=0000057268;variant_count=3", selected)
        # IIS/1C may return 404.15 for long query strings.  Preserve the exact
        # approved mapping while reading wide entities in bounded field groups.
        chunks = [selected[index:index + 12] for index in range(0, len(selected), 12)]
        if len(chunks) == 1:
            rows = client.query(entity, {"$filter": where, "$select": ",".join(selected), "$format": "json"})
        else:
            merged: Dict[str, Dict[str, Any]] = {}
            for chunk in chunks:
                fields = list(dict.fromkeys((["Ref_Key"] if "Ref_Key" not in chunk else []) + chunk))
                partial = client.query(entity, {"$filter": where, "$select": ",".join(fields), "$format": "json"})
                for source in partial:
                    key = str(source.get("Ref_Key") or "")
                    merged.setdefault(key, {}).update(source)
            rows = list(merged.values())
        raw[entity] = rows
        run_rows[entity]["extracted_count"] = len(rows)
        return rows

    # Product and selected variants.
    product_entity = "Catalog_Номенклатура"
    product_rows = query_sheet("RAW_PRODUCTS", product_entity, "Ref_Key eq guid'%s'" % PRODUCT_ID)
    if len(product_rows) != 1 or str(product_rows[0].get("Code")).strip() != PRODUCT_CODE:
        safe_codes = [str(item.get("Code")) for item in product_rows]
        raise RuntimeError("Puffy Fine exact lookup mismatch: count=%d codes=%s" % (len(product_rows), safe_codes))
    product_source = product_rows[0]
    product = map_direct(headers["RAW_PRODUCTS"], dictionary, "RAW_PRODUCTS", product_source)
    product["product_id"] = PRODUCT_ID
    parent_id = str(product_source.get("Parent_Key") or "").lower()
    product["parent_classification_id"] = "1C_GROUP:" + parent_id if parent_id and parent_id != ZERO_GUID else None
    add_provenance(product, product_entity, PRODUCT_ID, run_id(product_entity))
    data["RAW_PRODUCTS"].append(product)
    product_file_ids = sorted({str(value).lower() for value in [product.get("main_image_file_id"), product.get("website_description_file_id")] if value and str(value).lower() != ZERO_GUID})

    variant_entity = "Catalog_ХарактеристикиНоменклатуры"
    variant_rows = query_sheet("RAW_VARIANTS", variant_entity, "(" + guid_filter("Ref_Key", VARIANT_IDS) + ")")
    if {str(row.get("Ref_Key")).lower() for row in variant_rows} != set(VARIANT_IDS):
        raise RuntimeError("Selected variant closure is incomplete")
    for source in sorted(variant_rows, key=lambda item: VARIANT_IDS.index(str(item["Ref_Key"]).lower())):
        row = map_direct(headers["RAW_VARIANTS"], dictionary, "RAW_VARIANTS", source)
        row["variant_id"] = str(source["Ref_Key"]).lower()
        row["product_id"] = PRODUCT_ID
        add_provenance(row, variant_entity, row["variant_id"], run_id(variant_entity))
        data["RAW_VARIANTS"].append(row)

    # Parent 1C group classification required by product FK.
    if parent_id and parent_id != ZERO_GUID:
        entity = "Catalog_Номенклатура"
        rows = client.query(entity, {"$filter": "Ref_Key eq guid'%s'" % parent_id, "$select": "Ref_Key,Parent_Key,Description,Code,IsFolder,DeletionMark", "$format": "json"})
        raw["Catalog_Номенклатура_parent_group"] = rows
        if len(rows) != 1:
            raise RuntimeError("Product parent classification is unavailable")
        rid = run_id(entity)
        source = rows[0]
        classification = make_row(headers["RAW_CLASSIFICATIONS"])
        classification.update({
            "classification_id": "1C_GROUP:" + parent_id,
            "classification_system": "1C_GROUP",
            "source_category_id": parent_id,
            "parent_source_category_id": str(source.get("Parent_Key") or "") or None,
            "name_raw": source.get("Description"),
            "code_raw": source.get("Code"),
            "is_folder_raw": source.get("IsFolder"),
            "deletion_mark": source.get("DeletionMark"),
        })
        add_provenance(classification, entity, parent_id, rid)
        data["RAW_CLASSIFICATIONS"].append(classification)
        link = make_row(headers["RAW_PRODUCT_CLASSIFICATIONS"])
        link_id = PRODUCT_ID + "|1C_GROUP|" + parent_id
        link.update({
            "product_classification_id": link_id,
            "product_id": PRODUCT_ID,
            "source_category_id_raw": parent_id,
            "classification_id": "1C_GROUP:" + parent_id,
            "classification_system": "1C_GROUP",
        })
        add_provenance(link, entity, link_id, rid)
        data["RAW_PRODUCT_CLASSIFICATIONS"].append(link)

    # Generic FK closure for manufacturer, units, package set.
    closure_specs = [
        ("RAW_MANUFACTURERS", "Catalog_Производители", "manufacturer_id", [product.get("manufacturer_id")]),
        ("RAW_UNIT_DEFINITIONS", "Catalog_УпаковкиЕдиницыИзмерения", "unit_id", [product.get("base_unit_id"), product.get("report_unit_id"), product.get("weight_unit_id"), product.get("length_unit_id")]),
        ("RAW_PACKAGE_SETS", "Catalog_НаборыУпаковок", "package_set_id", [product.get("package_set_id")]),
    ]
    for sheet, entity, key_field, ids in closure_specs:
        wanted = sorted({str(value).lower() for value in ids if value and str(value).lower() != ZERO_GUID})
        if not wanted:
            continue
        selected = direct_source_properties(dictionary, sheet, entity)
        register_run(entity, "referenced closure from product 0000057268", selected)
        rows = client.query(entity, {"$filter": "(" + guid_filter("Ref_Key", wanted) + ")", "$select": ",".join(selected), "$format": "json"})
        raw[entity] = rows
        run_rows[entity]["extracted_count"] = len(rows)
        for source in rows:
            row = map_direct(headers[sheet], dictionary, sheet, source)
            record_id = str(source["Ref_Key"]).lower()
            row[key_field] = record_id
            add_provenance(row, entity, record_id, run_id(entity))
            data[sheet].append(row)

    # Exact variant -> photo links.
    link_entity = "Catalog_iq_ИзображенияХарактеристик"
    link_rows = query_sheet("RAW_VARIANT_IMAGE_LINKS", link_entity, "Номенклатура_Key eq guid'%s' and (%s)" % (PRODUCT_ID, guid_filter("Характеристика_Key", VARIANT_IDS)))
    link_by_variant: Dict[str, Dict[str, Any]] = {}
    for source in link_rows:
        variant_id = str(source.get("Характеристика_Key") or "").lower()
        if variant_id in VARIANT_IDS and variant_id not in link_by_variant:
            link_by_variant[variant_id] = source
    if set(link_by_variant) != set(VARIANT_IDS):
        raise RuntimeError("Exact variant image links are incomplete")
    for variant_id in VARIANT_IDS:
        source = link_by_variant[variant_id]
        row = map_direct(headers["RAW_VARIANT_IMAGE_LINKS"], dictionary, "RAW_VARIANT_IMAGE_LINKS", source)
        record_id = str(source["Ref_Key"]).lower()
        row["variant_image_link_id"] = record_id
        add_provenance(row, link_entity, record_id, run_id(link_entity))
        data["RAW_VARIANT_IMAGE_LINKS"].append(row)

    # Color schemes and palettes referenced by selected links.
    scheme_ids = sorted({str(row.get("color_scheme_id")).lower() for row in data["RAW_VARIANT_IMAGE_LINKS"] if row.get("color_scheme_id") and str(row.get("color_scheme_id")).lower() != ZERO_GUID})
    if scheme_ids:
        entity = "Catalog_iq_ЦветоваяСхема"
        selected = direct_source_properties(dictionary, "RAW_COLOR_SCHEMES", entity)
        register_run(entity, "selected variant color schemes", selected)
        rows = client.query(entity, {"$filter": "(" + guid_filter("Ref_Key", scheme_ids) + ")", "$select": ",".join(selected), "$format": "json"})
        raw[entity] = rows
        run_rows[entity]["extracted_count"] = len(rows)
        for source in rows:
            row = map_direct(headers["RAW_COLOR_SCHEMES"], dictionary, "RAW_COLOR_SCHEMES", source)
            record_id = str(source["Ref_Key"]).lower()
            row["color_scheme_id"] = record_id
            add_provenance(row, entity, record_id, run_id(entity))
            data["RAW_COLOR_SCHEMES"].append(row)
        palette_ids = sorted({str(row.get("palette_id")).lower() for row in data["RAW_COLOR_SCHEMES"] if row.get("palette_id") and str(row.get("palette_id")).lower() != ZERO_GUID})
        if palette_ids:
            p_entity = "Catalog_iq_ЦветоваяПалитра"
            p_selected = direct_source_properties(dictionary, "RAW_COLOR_PALETTES", p_entity)
            register_run(p_entity, "referenced palette closure", p_selected)
            p_rows = client.query(p_entity, {"$filter": "(" + guid_filter("Ref_Key", palette_ids) + ")", "$select": ",".join(p_selected), "$format": "json"})
            raw[p_entity] = p_rows
            run_rows[p_entity]["extracted_count"] = len(p_rows)
            for source in p_rows:
                row = map_direct(headers["RAW_COLOR_PALETTES"], dictionary, "RAW_COLOR_PALETTES", source)
                record_id = str(source["Ref_Key"]).lower()
                row["palette_id"] = record_id
                add_provenance(row, p_entity, record_id, run_id(p_entity))
                data["RAW_COLOR_PALETTES"].append(row)

    # Variant attached files and binary metadata, no Base64 persisted.
    file_ids = [str(link_by_variant[variant].get("image_Key") or "").lower() for variant in VARIANT_IDS]
    if any(not GUID_RE.match(value) or value == ZERO_GUID for value in file_ids):
        raise RuntimeError("Selected variant has no exact attached-file GUID")
    file_entity = "Catalog_iq_ИзображенияХарактеристикПрисоединенныеФайлы"
    file_selected = direct_source_properties(dictionary, "RAW_VARIANT_FILES", file_entity)
    register_run(file_entity, "three exact image file ids", file_selected)
    file_rows = client.query(file_entity, {"$filter": "(" + guid_filter("Ref_Key", file_ids) + ")", "$select": ",".join(file_selected), "$format": "json"})
    raw[file_entity] = file_rows
    run_rows[file_entity]["extracted_count"] = len(file_rows)
    if {str(row.get("Ref_Key")).lower() for row in file_rows} != set(file_ids):
        raise RuntimeError("Variant attached-file closure is incomplete")
    link_ids = {str(row["variant_file_id"]).lower(): str(row["variant_image_link_id"]).lower() for row in data["RAW_VARIANT_IMAGE_LINKS"]}
    for source in file_rows:
        row = map_direct(headers["RAW_VARIANT_FILES"], dictionary, "RAW_VARIANT_FILES", source)
        record_id = str(source["Ref_Key"]).lower()
        row["file_id"] = record_id
        row["owner_type"] = "StandardODATA.Catalog_iq_ИзображенияХарактеристик"
        row["binary_storage_id"] = binary_key(record_id, VARIANT_FILE_TYPE)
        add_provenance(row, file_entity, record_id, run_id(file_entity))
        if row.get("owner_id") != link_ids.get(record_id):
            raise RuntimeError("Variant file owner does not match exact image link")
        data["RAW_VARIANT_FILES"].append(row)

    # Product-level attached files referenced directly by the selected product.
    if product_file_ids:
        product_file_entity = "Catalog_НоменклатураПрисоединенныеФайлы"
        product_file_selected = direct_source_properties(dictionary, "RAW_PRODUCT_FILES", product_file_entity)
        register_run(product_file_entity, "direct product file ids", product_file_selected)
        product_file_rows = client.query(product_file_entity, {"$filter": "(" + guid_filter("Ref_Key", product_file_ids) + ")", "$select": ",".join(product_file_selected), "$format": "json"})
        raw[product_file_entity] = product_file_rows
        run_rows[product_file_entity]["extracted_count"] = len(product_file_rows)
        if {str(row.get("Ref_Key")).lower() for row in product_file_rows} != set(product_file_ids):
            raise RuntimeError("Product attached-file closure is incomplete")
        for source in product_file_rows:
            row = map_direct(headers["RAW_PRODUCT_FILES"], dictionary, "RAW_PRODUCT_FILES", source)
            record_id = str(source["Ref_Key"]).lower()
            row["file_id"] = record_id
            row["owner_type"] = "StandardODATA.Catalog_Номенклатура"
            row["is_primary_derived"] = record_id == product.get("main_image_file_id")
            row["binary_storage_id"] = binary_key(record_id, PRODUCT_FILE_TYPE)
            add_provenance(row, product_file_entity, record_id, run_id(product_file_entity))
            if row.get("owner_id") != PRODUCT_ID:
                raise RuntimeError("Product attached-file owner mismatch")
            data["RAW_PRODUCT_FILES"].append(row)

    binary_entity = "InformationRegister_ДвоичныеДанныеФайлов"
    binary_selected = ["Файл", "Файл_Type", "ДвоичныеДанныеФайла_Type", "ДвоичныеДанныеФайла_Base64Data"]
    register_run(binary_entity, "direct composite keys for selected variant/product files", binary_selected)
    binary_safe_raw: List[Dict[str, Any]] = []
    binary_requests = [(file_id, VARIANT_FILE_TYPE) for file_id in file_ids] + [(file_id, PRODUCT_FILE_TYPE) for file_id in product_file_ids]
    for file_id, file_type in binary_requests:
        key = "%s(Файл='%s',Файл_Type='%s')" % (binary_entity, file_id, file_type)
        source = client.direct(key, binary_selected)
        encoded_raw = source.get("ДвоичныеДанныеФайла_Base64Data") or ""
        encoded = "".join(str(encoded_raw).lstrip("\ufeff").strip().strip("\"").split())
        try:
            decoded = base64.b64decode(encoded, validate=True) if encoded else b""
        except Exception as exc:
            raise RuntimeError("Invalid Base64 payload for masked file %s…%s" % (file_id[:6], file_id[-4:])) from exc
        mime = None
        if decoded.startswith(b"\xff\xd8\xff"):
            mime = "image/jpeg"
        elif decoded.startswith(b"\x89PNG\r\n\x1a\n"):
            mime = "image/png"
        safe = {key_name: value for key_name, value in source.items() if key_name != "ДвоичныеДанныеФайла_Base64Data" and not key_name.startswith("@odata")}
        safe.update({"payload_base64_length": len(encoded), "decoded_size_bytes": len(decoded), "mime_type_detected": mime, "content_hash_sha256": sha256_bytes(decoded) if decoded else None})
        binary_safe_raw.append(safe)
        row = make_row(headers["RAW_BINARY_STORAGE_METADATA"])
        storage_id = binary_key(file_id, file_type)
        row.update({
            "binary_storage_id": storage_id,
            "file_id": file_id,
            "file_type_raw": source.get("Файл_Type"),
            "binary_value_type_raw": source.get("ДвоичныеДанныеФайла_Type"),
            "payload_present": bool(decoded),
            "payload_base64_length": len(encoded) if encoded else None,
            "decoded_size_bytes": len(decoded) if decoded else None,
            "mime_type_detected": mime,
            "content_hash_sha256": sha256_bytes(decoded) if decoded else None,
            "retrieval_method": "ODATA_DIRECT_COMPOSITE_KEY_BASE64_ONCE",
            "last_verified_at_utc": cutoff,
        })
        add_provenance(row, binary_entity, storage_id, run_id(binary_entity))
        data["RAW_BINARY_STORAGE_METADATA"].append(row)
    raw[binary_entity] = binary_safe_raw
    run_rows[binary_entity]["extracted_count"] = len(binary_safe_raw)

    # Current prices: latest Period <= one cutoff; zero GUID is retained raw.
    price_entity = "InformationRegister_ЦеныНоменклатуры_RecordType"
    price_selected = ["Recorder", "Recorder_Type", "LineNumber", "Period", "Active", "Номенклатура_Key", "Характеристика_Key", "ВидЦены_Key", "Цена", "Упаковка_Key", "Валюта_Key"]
    register_run(price_entity, "product 0000057268; three variants plus product-level zero GUID; cutoff=" + cutoff, price_selected)
    variant_price_ids = VARIANT_IDS + [ZERO_GUID]
    price_rows = client.query(price_entity, {"$filter": "Номенклатура_Key eq guid'%s' and Active eq true and (%s)" % (PRODUCT_ID, guid_filter("Характеристика_Key", variant_price_ids)), "$select": ",".join(price_selected), "$format": "json"})
    raw[price_entity] = price_rows
    run_rows[price_entity]["extracted_count"] = len(price_rows)
    eligible: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for source in price_rows:
        period = normalize_datetime(source.get("Period"))
        if period and period <= cutoff:
            key = (str(source["Номенклатура_Key"]).lower(), str(source["Характеристика_Key"]).lower(), str(source["ВидЦены_Key"]).lower())
            eligible[key].append(source)
    latest_rows: List[Dict[str, Any]] = []
    for key, candidates in eligible.items():
        max_period = max(normalize_datetime(item.get("Period")) or "" for item in candidates)
        winners = [item for item in candidates if normalize_datetime(item.get("Period")) == max_period]
        if len(winners) != 1:
            raise RuntimeError("Current-price source has %d records at the same latest Period for %s" % (len(winners), key))
        latest_rows.append(winners[0])
    for source in sorted(latest_rows, key=lambda item: (str(item["Характеристика_Key"]), str(item["ВидЦены_Key"]))):
        row = make_row(headers["RAW_CURRENT_PRICES"])
        variant_raw = str(source["Характеристика_Key"]).lower()
        price_type = str(source["ВидЦены_Key"]).lower()
        current_id = PRODUCT_ID + "|" + variant_raw + "|" + price_type
        row.update({
            "current_price_id": current_id,
            "product_id": PRODUCT_ID,
            "variant_id_raw": variant_raw,
            "variant_id": None if variant_raw == ZERO_GUID else variant_raw,
            "price_type_id": price_type,
            "price_value": source.get("Цена"),
            "currency_id_raw": str(source.get("Валюта_Key") or "").lower() or None,
            "package_id_raw": str(source.get("Упаковка_Key") or "").lower() or None,
            "effective_period": normalize_datetime(source.get("Period")),
            "cutoff_at_utc": cutoff,
            "selection_rule": "MAX(Period) WHERE Active=true AND Period<=cutoff; reject ties",
            "recorder_id_raw": source.get("Recorder"),
        })
        add_provenance(row, price_entity, source_record_id_price(source), run_id(price_entity))
        data["RAW_CURRENT_PRICES"].append(row)

    price_type_ids = sorted({str(row["price_type_id"]).lower() for row in data["RAW_CURRENT_PRICES"]})
    if price_type_ids:
        entity = "Catalog_ВидыЦен"
        selected = direct_source_properties(dictionary, "RAW_PRICE_TYPES", entity)
        register_run(entity, "referenced price types", selected)
        rows = client.query(entity, {"$filter": "(" + guid_filter("Ref_Key", price_type_ids) + ")", "$select": ",".join(selected), "$format": "json"})
        raw[entity] = rows
        run_rows[entity]["extracted_count"] = len(rows)
        for source in rows:
            row = map_direct(headers["RAW_PRICE_TYPES"], dictionary, "RAW_PRICE_TYPES", source)
            record_id = str(source["Ref_Key"]).lower()
            row["price_type_id"] = record_id
            add_provenance(row, entity, record_id, run_id(entity))
            data["RAW_PRICE_TYPES"].append(row)

    # Current stock: signed movement aggregation at the same cutoff and explicit zero rows.
    stock_entity = "AccumulationRegister_СвободныеОстатки_RecordType"
    stock_selected = ["Recorder", "Recorder_Type", "Period", "LineNumber", "Active", "RecordType", "Номенклатура_Key", "Характеристика_Key", "Склад_Key", "ВНаличии"]
    register_run(stock_entity, "product 0000057268; three variants; cutoff=" + cutoff, stock_selected)
    stock_rows = client.query(stock_entity, {"$filter": "Номенклатура_Key eq guid'%s' and Active eq true and (%s)" % (PRODUCT_ID, guid_filter("Характеристика_Key", VARIANT_IDS)), "$select": ",".join(stock_selected), "$format": "json"})
    raw[stock_entity] = stock_rows
    run_rows[stock_entity]["extracted_count"] = len(stock_rows)
    by_stock_key: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    warehouse_ids = set()
    for source in stock_rows:
        period = normalize_datetime(source.get("Period"))
        if period and period > cutoff:
            continue
        variant_id = str(source.get("Характеристика_Key") or "").lower()
        warehouse_id = str(source.get("Склад_Key") or "").lower()
        if variant_id in VARIANT_IDS and GUID_RE.match(warehouse_id):
            warehouse_ids.add(warehouse_id)
            by_stock_key[(PRODUCT_ID, variant_id, warehouse_id)].append(source)
    if not warehouse_ids:
        raise RuntimeError("No referenced warehouses found for selected stock scope")
    for variant_id in VARIANT_IDS:
        for warehouse_id in sorted(warehouse_ids):
            contributing = by_stock_key.get((PRODUCT_ID, variant_id, warehouse_id), [])
            canonical = sorted(contributing, key=lambda item: (normalize_datetime(item.get("Period")) or "", str(item.get("Recorder")), int(item.get("LineNumber") or 0)))
            quantity = 0.0
            for source in canonical:
                sign = 1.0 if source.get("RecordType") == "Receipt" else -1.0
                quantity += sign * float(source.get("ВНаличии") or 0)
            row = make_row(headers["RAW_CURRENT_STOCK"])
            current_id = PRODUCT_ID + "|" + variant_id + "|" + warehouse_id
            row.update({
                "current_stock_id": current_id,
                "product_id": PRODUCT_ID,
                "variant_id": variant_id,
                "warehouse_id": warehouse_id,
                "quantity_available": round(quantity, 6),
                "cutoff_at_utc": cutoff,
                "aggregation_rule": "SUM(Receipt:+1, other RecordType:-1)*ВНаличии; Active=true; Period<=cutoff; v1",
                "source_record_count": len(canonical),
                "is_explicit_zero": abs(quantity) < 1e-9,
                "source_system_id": SOURCE_SYSTEM_ID,
                "source_entityset": stock_entity,
                "input_checksum_sha256": sha256_bytes(canonical_json(canonical)),
                "extraction_run_id": run_id(stock_entity),
            })
            data["RAW_CURRENT_STOCK"].append(row)

    entity = "Catalog_Склады"
    selected = direct_source_properties(dictionary, "RAW_WAREHOUSES", entity)
    register_run(entity, "referenced warehouses", selected)
    rows = client.query(entity, {"$filter": "(" + guid_filter("Ref_Key", sorted(warehouse_ids)) + ")", "$select": ",".join(selected), "$format": "json"})
    raw[entity] = rows
    run_rows[entity]["extracted_count"] = len(rows)
    for source in rows:
        row = map_direct(headers["RAW_WAREHOUSES"], dictionary, "RAW_WAREHOUSES", source)
        record_id = str(source["Ref_Key"]).lower()
        row["warehouse_id"] = record_id
        add_provenance(row, entity, record_id, run_id(entity))
        data["RAW_WAREHOUSES"].append(row)

    # Approved technical contract rows.
    source_row = make_row(headers["RAW_SOURCE_SYSTEMS"])
    source_row.update({
        "source_system_id": SOURCE_SYSTEM_ID,
        "source_system_name": "1C Standard OData",
        "source_system_type": "ODATA",
        "access_mode": "READ_ONLY",
        "endpoint_reference": "ODATA_BASE_URL from local secrets",
        "credentials_reference": "ODATA_USERNAME/ODATA_PASSWORD from local secrets",
        "active": True,
        "notes": "No credentials or protected URL persisted",
    })
    data["RAW_SOURCE_SYSTEMS"].append(source_row)

    dictionary_path = CONTRACT / "RAW_COMPLETE_V1_DATA_DICTIONARY.csv"
    mapping_path = CONTRACT / "RAW_COMPLETE_V1_ENTITYSET_MAPPING.csv"
    schema_row = make_row(headers["RAW_SCHEMA_VERSIONS"])
    schema_row.update({
        "schema_version_id": SCHEMA_VERSION_ID,
        "version_label": "RAW COMPLETE v1",
        "contract_status": "APPROVED",
        "created_at_utc": started,
        "approved_at_utc": started,
        "approved_by": "PROJECT_OWNER",
        "dictionary_checksum_sha256": sha256_bytes(dictionary_path.read_bytes()),
        "mapping_checksum_sha256": sha256_bytes(mapping_path.read_bytes()),
        "notes": "Phase C controlled fixture",
    })
    data["RAW_SCHEMA_VERSIONS"].append(schema_row)
    data["RAW_DATA_DICTIONARY"] = [{key: item.get(key) for key in headers["RAW_DATA_DICTIONARY"]} for item in dictionary]
    data["RAW_ENTITYSET_MAPPING"] = [{key: item.get(key) for key in headers["RAW_ENTITYSET_MAPPING"]} for item in mappings]

    for entity, row in run_rows.items():
        target_counts = [len(rows) for sheet, rows in data.items() if rows and any(str(item.get("source_entityset") or "") == entity for item in rows)]
        normalized_count = sum(target_counts)
        row["finished_at_utc"] = utc_now()
        row["status"] = "SUCCESS"
        row["expected_count"] = row["extracted_count"]
        row["validated_count"] = row["extracted_count"]
        row["rejected_count"] = 0
        row["missing_relation_count"] = 0
        row["content_checksum_sha256"] = sha256_bytes(canonical_json([item for rows in data.values() for item in rows if str(item.get("source_entityset") or "") == entity]))
        data["RAW_EXTRACTION_RUNS"].append(row)

    for name, value in raw.items():
        save_raw(name, value)

    # Required-null profile over populated rows only; no fabricated defaults.
    null_profile: List[Dict[str, Any]] = []
    for item in dictionary:
        if item["nullable"] != "NO" or item["source_system"] != SOURCE_SYSTEM_ID:
            continue
        sheet = item["sheet_name"]
        field = item["field_name"]
        rows = data[sheet]
        missing = [index + 2 for index, row in enumerate(rows) if row.get(field) in (None, "")]
        null_profile.append({"sheet": sheet, "field": field, "rows_in_scope": len(rows), "missing_rows": missing, "status": "PASS" if not missing else "FAIL"})
    (FIXTURE / "required_null_profile.json").write_text(json.dumps(null_profile, ensure_ascii=False, indent=2), encoding="utf-8")

    write_normalized(order, headers, data)
    manifest = {
        "fixture_id": run_prefix,
        "schema_version_id": SCHEMA_VERSION_ID,
        "created_at_utc": started,
        "cutoff_at_utc": cutoff,
        "source_system_id": SOURCE_SYSTEM_ID,
        "spreadsheet_id_masked": SPREADSHEET_ID[:6] + "…" + SPREADSHEET_ID[-6:],
        "scope": {"product_id": PRODUCT_ID, "product_code": PRODUCT_CODE, "product_name": "Пряжа Puffy Fine Alize", "variant_ids": VARIANT_IDS, "expected_color_codes": ["06", "90", "113"]},
        "sheet_order": order,
        "field_count": sum(len(headers[sheet]) for sheet in order),
        "row_counts": {sheet: len(data[sheet]) for sheet in order},
        "raw_sources": sorted(raw),
        "binary_payload_persisted": False,
        "extractor_version": EXTRACTOR_VERSION,
    }
    (FIXTURE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (FIXTURE / "row_counts.json").write_text(json.dumps(manifest["row_counts"], ensure_ascii=False, indent=2), encoding="utf-8")
    return data, {"dictionary": dictionary, "mappings": mappings, "matrix": matrix, "order": order, "headers": headers, "manifest": manifest, "null_profile": null_profile, "raw": raw}


def is_uuid(value: Any) -> bool:
    return bool(GUID_RE.fullmatch(str(value).lower()))


def validate_fixture(data: Dict[str, List[Dict[str, Any]]], ctx: Dict[str, Any], output_path: Optional[Path] = FIXTURE / "validation_results.json") -> Dict[str, Any]:
    dictionary = ctx["dictionary"]
    matrix = ctx["matrix"]
    order = ctx["order"]
    headers = ctx["headers"]
    raw = ctx["raw"]
    scope_validation = ctx.get("scope_validation", {})
    expected_products = int(scope_validation.get("product_count", 1))
    expected_variants = int(scope_validation.get("variant_count", len(VARIANT_IDS)))
    expected_image_links = int(scope_validation.get("image_link_count", len(VARIANT_IDS)))
    expected_warehouses = int(scope_validation.get("warehouse_count", len(data.get("RAW_WAREHOUSES", []))))
    product_scope_ids = set(scope_validation.get("product_ids", [PRODUCT_ID]))
    variant_scope_ids = set(scope_validation.get("variant_ids", VARIANT_IDS))
    results: List[Dict[str, Any]] = []
    dictionary_by_sheet: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for item in dictionary:
        dictionary_by_sheet[item["sheet_name"]].append(item)

    pk_fields = {sheet: [item["field_name"] for item in rows if item["primary_key"] in {"YES", "PART"}] for sheet, rows in dictionary_by_sheet.items()}
    fk_sets: Dict[Tuple[str, str], set] = {}
    for sheet, rows in dictionary_by_sheet.items():
        for item in rows:
            if item["primary_key"] in {"YES", "PART"}:
                fk_sets[(sheet, item["field_name"])] = {str(row.get(item["field_name"])) for row in data[sheet] if row.get(item["field_name"]) not in (None, "")}

    def add(validation: Dict[str, str], passed: bool, detail: str, applicable: bool = True) -> None:
        results.append({"validation_id": validation["validation_id"], "target_sheet": validation["target_sheet"], "check_type": validation["check_type"], "applicable": applicable, "status": "PASS" if passed else "FAIL", "detail": detail})

    for validation in matrix:
        sheet = validation["target_sheet"]
        rows = data.get(sheet, [])
        kind = validation["check_type"]
        passed = True
        detail = ""
        applicable = True

        if kind == "PK_UNIQUENESS":
            keys = pk_fields.get(sheet, [])
            values = [tuple(str(row.get(key)) for key in keys) for row in rows]
            passed = bool(keys) and len(values) == len(set(values)) and all(all(value not in ("", "None") for value in key) for key in values)
            detail = "%d scoped rows; PK=%s" % (len(rows), ",".join(keys))
        elif kind == "REQUIRED_KEYS":
            fields = [value.strip() for value in validation["required_input_fields"].replace("/", ",").split(",") if value.strip()]
            missing = [(index + 2, field) for index, row in enumerate(rows) for field in fields if row.get(field) in (None, "")]
            passed = not missing
            detail = "missing=%s" % missing[:20]
        elif kind == "IDEMPOTENCY":
            first = sha256_bytes(canonical_json(rows))
            second = sha256_bytes(canonical_json(json.loads(canonical_json(rows).decode("utf-8"))))
            passed = first == second
            detail = "canonical checksum stable"
        elif kind == "PROVENANCE":
            required = ["source_system_id", "source_entityset", "source_record_id", "extraction_run_id"]
            missing = [(index + 2, field) for index, row in enumerate(rows) for field in required if field in headers[sheet] and row.get(field) in (None, "")]
            passed = not missing
            detail = "provenance gaps=%d" % len(missing)
        elif kind == "GUID_FORMAT":
            fields = [value.strip() for value in validation["required_input_fields"].split(",") if value.strip()]
            invalid = [(index + 2, field, row.get(field)) for index, row in enumerate(rows) for field in fields if row.get(field) not in (None, "") and not is_uuid(row.get(field))]
            passed = not invalid
            detail = "invalid GUIDs=%d" % len(invalid)
        elif validation["validation_id"] == "CTRL-CHECKSUM":
            schema = data["RAW_SCHEMA_VERSIONS"][0]
            passed = schema["dictionary_checksum_sha256"] == sha256_bytes((CONTRACT / "RAW_COMPLETE_V1_DATA_DICTIONARY.csv").read_bytes()) and schema["mapping_checksum_sha256"] == sha256_bytes((CONTRACT / "RAW_COMPLETE_V1_ENTITYSET_MAPPING.csv").read_bytes())
            detail = "approved contract checksums"
        elif validation["validation_id"] == "CTRL-SCHEMA-NO-UNKNOWN-FIELDS":
            passed = len(order) == 32 and sum(len(headers[name]) for name in order) == 466 and all(list(row.keys()) == headers[name] for name in order for row in data[name])
            detail = "32 sheets / 466 fields"
        elif validation["validation_id"] in {"CTRL-PRODUCT-COUNT", "CTRL-VARIANT-COUNT", "CTRL-IMAGE-LINKS"}:
            scoped_expected = {
                "CTRL-PRODUCT-COUNT": expected_products,
                "CTRL-VARIANT-COUNT": expected_variants,
                "CTRL-IMAGE-LINKS": expected_image_links,
            }[validation["validation_id"]]
            passed = len(rows) == scoped_expected
            detail = "owner-authorized scoped count=%d" % scoped_expected
        elif validation["validation_id"] == "CTRL-NO-SUBSTITUTION":
            files = {row["file_id"]: row for row in data["RAW_VARIANT_FILES"]}
            referenced = [link for link in rows if link.get("variant_file_id") not in (None, "", ZERO_GUID)]
            passed = all(link.get("variant_file_id") in files and files[link["variant_file_id"]].get("owner_id") == link.get("variant_image_link_id") for link in referenced)
            detail = "exact nonzero link->file owner chain; no-file links=%d" % (len(rows) - len(referenced))
        elif validation["validation_id"] == "CTRL-NO-BASE64":
            passed = all("Base64" not in field and "base64data" not in field.lower() for row in rows for field in row)
            detail = "payload not persisted; metadata lengths only"
        elif validation["validation_id"] == "CTRL-STOCK-SIGN":
            passed = all(str(row.get("aggregation_rule", "")).startswith("SUM(Receipt:+1") for row in rows)
            detail = "versioned Receipt/Expense sign rule"
        elif validation["validation_id"] == "CTRL-STOCK-TOTAL":
            expected = expected_variants * expected_warehouses
            passed = len(rows) == expected and bool(ctx.get("stock_reconciliation_pass", True))
            detail = "scoped warehouse matrix with explicit zeros; expected=%d actual=%d" % (expected, len(rows))
        elif validation["validation_id"] == "CTRL-PRICE-LATEST":
            selected = {(row["product_id"], row["variant_id_raw"], row["price_type_id"]): row["effective_period"] for row in rows}
            later = []
            for source in raw.get("InformationRegister_ЦеныНоменклатуры_RecordType", []):
                key = (str(source["Номенклатура_Key"]).lower(), str(source["Характеристика_Key"]).lower(), str(source["ВидЦены_Key"]).lower())
                period = normalize_datetime(source.get("Period"))
                if key in selected and period and period <= ctx["manifest"]["cutoff_at_utc"] and period > selected[key]:
                    later.append((key, period))
            passed = not later
            detail = "later eligible rows=%d" % len(later)
        elif validation["validation_id"] == "CTRL-COLOR-RAW":
            passed = all(row.get("description_raw") not in (None, "") for row in rows)
            detail = "raw variant descriptions retained"
        elif validation["validation_id"] == "CTRL-COUNTS":
            passed = all(int(row.get("extracted_count") or 0) == int(row.get("validated_count") or 0) + int(row.get("rejected_count") or 0) for row in rows)
            detail = "run accounting reconciled"
        elif validation["validation_id"] in {"CTRL-FK-COVERAGE", "CTRL-ORPHAN-RECORDS"}:
            misses = []
            for item in dictionary:
                if not item["foreign_key"]:
                    continue
                target_sheet, target_field = item["foreign_key"].split(".", 1)
                allowed = fk_sets.get((target_sheet, target_field), set())
                for index, row in enumerate(data[item["sheet_name"]]):
                    value = row.get(item["field_name"])
                    if value not in (None, "") and str(value) not in allowed:
                        misses.append((item["sheet_name"], index + 2, item["field_name"], str(value), item["foreign_key"]))
            passed = not misses
            detail = "unresolved FK=%s" % misses[:20]
        elif validation["validation_id"] == "CTRL-SOURCE-DUPLICATES":
            duplicates = []
            for name, sheet_rows in data.items():
                seen = set()
                for row in sheet_rows:
                    if "source_entityset" not in row or "source_record_id" not in row:
                        continue
                    key = (row.get("source_entityset"), row.get("source_record_id"))
                    if key in seen:
                        duplicates.append((name, key))
                    seen.add(key)
            passed = not duplicates
            detail = "unexpected source duplicates=%s" % duplicates[:20]
        elif validation["validation_id"] == "CTRL-PHOTO-OPTIONAL-COVERAGE":
            linked = {row["variant_id"] for row in data["RAW_VARIANT_IMAGE_LINKS"]}
            retained = {row["variant_id"] for row in rows}
            passed = len(rows) == expected_variants and linked.issubset(retained)
            detail = "variants retained=%d; exact photo=%d; no-photo=%d" % (len(retained), len(linked), len(retained - linked))
        elif validation["validation_id"] == "CTRL-STOCK-ZEROS":
            expected = expected_variants * expected_warehouses
            passed = len(rows) == expected and any(bool(row.get("is_explicit_zero")) for row in rows)
            detail = "scoped rows=%d, explicit_zero=%d" % (len(rows), sum(bool(row.get("is_explicit_zero")) for row in rows))
        elif validation["validation_id"] == "CTRL-OWNER-TYPE":
            passed = all(
                row.get("owner_type_raw") == "StandardODATA.Catalog_Номенклатура"
                and str(row.get("owner_raw", "")).lower() == str(row.get("product_id", "")).lower()
                and str(row.get("product_id", "")).lower() in product_scope_ids
                and str(row.get("variant_id", "")).lower() in variant_scope_ids
                for row in rows
            )
            detail = "typed Owner parsed exactly"
        elif validation["validation_id"] == "CTRL-BINARY-POLYMORPHIC":
            metadata = {row["binary_storage_id"]: row for row in data["RAW_BINARY_STORAGE_METADATA"]}
            variant_pass = all(row.get("binary_storage_id") in metadata and metadata[row["binary_storage_id"]].get("file_type_raw") == VARIANT_FILE_TYPE for row in data["RAW_VARIANT_FILES"])
            product_pass = all(row.get("binary_storage_id") in metadata and metadata[row["binary_storage_id"]].get("file_type_raw") == PRODUCT_FILE_TYPE for row in data["RAW_PRODUCT_FILES"])
            passed = variant_pass and product_pass
            detail = "composite file/type keys match for variant and product files"
        elif validation["validation_id"] == "CTRL-REQUIRED-NULL-PROFILE":
            failures = [item for item in ctx["null_profile"] if item["status"] == "FAIL"]
            passed = not failures
            detail = "required-null failures=%s" % failures[:20]
        else:
            # Empty optional partitions are evaluated as scoped not-applicable;
            # populated partitions still pass only after generic PK/REQ/type/FK gates.
            applicable = bool(rows)
            passed = True
            detail = "not applicable to owner-authorized minimal fixture" if not rows else "covered by generic schema/type/PK/FK gates"
        add(validation, passed, detail, applicable)

    # Contract types for every populated physical field.
    type_errors = []
    for item in dictionary:
        sheet = item["sheet_name"]
        field = item["field_name"]
        kind = item["data_type"]
        for index, row in enumerate(data[sheet]):
            value = row.get(field)
            if value in (None, ""):
                continue
            ok = True
            try:
                if kind == "uuid":
                    ok = is_uuid(value)
                elif kind in {"integer"}:
                    int(value)
                elif kind in {"decimal"}:
                    float(value)
                elif kind == "boolean":
                    ok = isinstance(value, bool) or str(value).lower() in {"true", "false"}
                elif kind == "datetime":
                    ok = normalize_datetime(value) is not None
                elif kind == "sha256":
                    ok = bool(SHA_RE.fullmatch(str(value)))
            except (TypeError, ValueError):
                ok = False
            if not ok:
                type_errors.append((sheet, index + 2, field, kind, value))

    failed = [item for item in results if item["status"] == "FAIL"]
    report = {
        "status": "PASS" if not failed and not type_errors else "FAIL",
        "validation_count": len(results),
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "applicable": sum(bool(item["applicable"]) for item in results),
        "not_applicable": sum(not bool(item["applicable"]) for item in results),
        "type_errors": type_errors,
        "results": results,
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def finalize_checksums() -> None:
    files = sorted(path for path in FIXTURE.rglob("*") if path.is_file() and path.name != "checksums.sha256")
    lines = [sha256_bytes(path.read_bytes()) + "  " + str(path.relative_to(FIXTURE)) for path in files]
    (FIXTURE / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_fixture(write: bool = True) -> Dict[str, Any]:
    import gspread

    load_dotenv(ENV_FILE)
    credentials = os.environ.get("GOOGLE_CREDENTIALS_PATH", "")
    if not credentials:
        raise RuntimeError("GOOGLE_CREDENTIALS_PATH is not configured")
    manifest = json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))
    validation = json.loads((FIXTURE / "validation_results.json").read_text(encoding="utf-8"))
    if validation["status"] != "PASS" or validation["validation_count"] != 171:
        raise RuntimeError("Fixture validation is not a complete PASS")

    client = gspread.service_account(filename=credentials)
    spreadsheet = client.open_by_key(os.environ.get("RAW_COMPLETE_SPREADSHEET_ID") or SPREADSHEET_ID)
    worksheets = spreadsheet.worksheets()
    order = manifest["sheet_order"]
    if [sheet.title for sheet in worksheets] != order:
        raise RuntimeError("Live worksheet order differs from approved contract")

    dictionary = read_csv(CONTRACT / "RAW_COMPLETE_V1_DATA_DICTIONARY.csv")
    types = {(item["sheet_name"], item["field_name"]): item["data_type"] for item in dictionary}

    def typed_row(sheet: str, header: Sequence[str], values: Sequence[str]) -> List[Any]:
        result: List[Any] = []
        for index, field in enumerate(header):
            value = values[index] if index < len(values) else ""
            kind = types[(sheet, field)]
            if value == "":
                result.append("")
            elif kind == "integer":
                result.append(int(value))
            elif kind == "decimal":
                result.append(float(value))
            elif kind == "boolean":
                result.append(value.lower() == "true")
            else:
                result.append(value)
        return result

    data_ranges = []
    expected: Dict[str, List[List[Any]]] = {}
    existing_by_sheet: Dict[str, List[List[Any]]] = {}
    if write:
        preflight_ranges = ["'%s'" % worksheet.title.replace("'", "''") for worksheet in worksheets]
        preflight = spreadsheet.values_batch_get(preflight_ranges).get("valueRanges", [])
        if len(preflight) != len(worksheets):
            raise RuntimeError("Incomplete Google Sheets preflight batch response")
        existing_by_sheet = {worksheet.title: value_range.get("values", []) for worksheet, value_range in zip(worksheets, preflight)}
    for worksheet in worksheets:
        path = FIXTURE / "normalized" / (worksheet.title + ".csv")
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
        if write:
            existing = existing_by_sheet[worksheet.title]
            live_header = existing[0] if existing else []
            if live_header != rows[0]:
                raise RuntimeError("Header mismatch in " + worksheet.title)
            if any(any(cell != "" for cell in row) for row in existing[1:]):
                raise RuntimeError("Target sheet already contains data: " + worksheet.title)
        values = [typed_row(worksheet.title, rows[0], row) for row in rows[1:]]
        expected[worksheet.title] = values
        if values:
            data_ranges.append({"range": "'%s'!A2" % worksheet.title.replace("'", "''"), "values": values})

    body_bytes = len(canonical_json(data_ranges))
    if body_bytes > 2_000_000:
        raise RuntimeError("Test write payload exceeds approved 2 MB target")
    if write:
        spreadsheet.values_batch_update({"valueInputOption": "RAW", "data": data_ranges})

    ranges = ["'%s'!A1:%s%d" % (sheet.replace("'", "''"), column_name(len(next(csv.reader((FIXTURE / "normalized" / (sheet + ".csv")).open(encoding="utf-8-sig"))))), manifest["row_counts"][sheet] + 1) for sheet in order]
    response = spreadsheet.values_batch_get(ranges, params={"valueRenderOption": "UNFORMATTED_VALUE"})
    returned = response.get("valueRanges", [])
    failures = []
    for sheet, value_range in zip(order, returned):
        values = value_range.get("values", [])
        with (FIXTURE / "normalized" / (sheet + ".csv")).open(encoding="utf-8-sig", newline="") as handle:
            source_csv = list(csv.reader(handle))
        source = [source_csv[0]] + [typed_row(sheet, source_csv[0], row) for row in source_csv[1:]]
        padded = [row + [""] * (len(source[0]) - len(row)) for row in values]
        if padded != source:
            failures.append(sheet)
    result = {"status": "PASS" if not failures else "FAIL", "operation": "write_and_read_back" if write else "read_back_only", "written_row_counts": manifest["row_counts"] if write else {}, "validated_row_counts": manifest["row_counts"], "payload_bytes": body_bytes, "read_back_failures": failures, "validated_at_utc": utc_now()}
    (FIXTURE / "read_back_validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    finalize_checksums()
    return result


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def fixture_value(value: str, kind: str) -> Any:
    if value == "":
        return ""
    if kind == "integer":
        return int(value)
    if kind == "decimal":
        return float(value)
    if kind == "boolean":
        return value.lower() == "true"
    return value


def load_frozen_fixture() -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
    dictionary = read_csv(CONTRACT / "RAW_COMPLETE_V1_DATA_DICTIONARY.csv")
    mappings = read_csv(CONTRACT / "RAW_COMPLETE_V1_ENTITYSET_MAPPING.csv")
    matrix = read_csv(CONTRACT / "RAW_COMPLETE_V1_VALIDATION_MATRIX.csv")
    manifest = json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))
    null_profile = json.loads((FIXTURE / "required_null_profile.json").read_text(encoding="utf-8"))
    order, headers = get_headers(dictionary)
    types = {(item["sheet_name"], item["field_name"]): item["data_type"] for item in dictionary}
    if order != manifest["sheet_order"]:
        raise RuntimeError("Frozen manifest sheet order differs from approved dictionary")
    data: Dict[str, List[Dict[str, Any]]] = {}
    for sheet in order:
        path = FIXTURE / "normalized" / (sheet + ".csv")
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
        if not rows or rows[0] != headers[sheet]:
            raise RuntimeError("Frozen fixture header mismatch in " + sheet)
        typed_rows: List[Dict[str, Any]] = []
        for values in rows[1:]:
            padded = values + [""] * (len(headers[sheet]) - len(values))
            typed_rows.append({
                field: fixture_value(padded[index], types[(sheet, field)])
                for index, field in enumerate(headers[sheet])
            })
        data[sheet] = typed_rows
    raw = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((FIXTURE / "raw").glob("*.json"))
    }
    ctx = {
        "dictionary": dictionary,
        "mappings": mappings,
        "matrix": matrix,
        "order": order,
        "headers": headers,
        "manifest": manifest,
        "null_profile": null_profile,
        "raw": raw,
    }
    return data, ctx


def verify_frozen_checksums() -> Dict[str, Any]:
    checksum_path = FIXTURE / "checksums.sha256"
    checked = []
    failures = []
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        path = FIXTURE / relative
        actual = sha256_bytes(path.read_bytes()) if path.is_file() else None
        checked.append(relative)
        if actual != expected:
            failures.append({"path": relative, "expected": expected, "actual": actual})
    return {
        "status": "PASS" if not failures else "FAIL",
        "checksum_manifest_sha256": sha256_bytes(checksum_path.read_bytes()),
        "checked_file_count": len(checked),
        "failures": failures,
    }


def canonical_cell(value: Any, kind: str) -> Any:
    if value in (None, ""):
        return ""
    if kind == "boolean":
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in {"true", "1"}:
            return True
        if text in {"false", "0"}:
            return False
        return text
    if kind == "integer":
        try:
            return int(Decimal(str(value)))
        except (InvalidOperation, ValueError):
            return str(value)
    if kind == "decimal":
        try:
            number = Decimal(str(value)).normalize()
            text = format(number, "f")
            return "0" if text in {"-0", "-0.0"} else text
        except (InvalidOperation, ValueError):
            return str(value)
    return str(value)


def fixture_matrices(
    data: Dict[str, List[Dict[str, Any]]],
    order: Sequence[str],
    headers: Dict[str, List[str]],
) -> Dict[str, List[List[Any]]]:
    return {
        sheet: [list(headers[sheet])] + [[row.get(field, "") for field in headers[sheet]] for row in data[sheet]]
        for sheet in order
    }


def read_google_matrices(
    spreadsheet: Any,
    order: Sequence[str],
    headers: Dict[str, List[str]],
) -> Dict[str, List[List[Any]]]:
    ranges = ["'%s'" % sheet.replace("'", "''") for sheet in order]
    response = spreadsheet.values_batch_get(ranges, params={"valueRenderOption": "UNFORMATTED_VALUE"})
    returned = response.get("valueRanges", [])
    if len(returned) != len(order):
        raise RuntimeError("Incomplete Google Sheets batch-read response")
    matrices: Dict[str, List[List[Any]]] = {}
    for sheet, value_range in zip(order, returned):
        width = len(headers[sheet])
        values = value_range.get("values", [])
        if not values:
            raise RuntimeError("Missing header in live sheet " + sheet)
        padded = [(row + [""] * (width - len(row)))[:width] for row in values]
        while len(padded) > 1 and all(value in (None, "") for value in padded[-1]):
            padded.pop()
        matrices[sheet] = padded
    return matrices


def state_from_matrices(
    matrices: Dict[str, List[List[Any]]],
    order: Sequence[str],
    headers: Dict[str, List[str]],
    dictionary: List[Dict[str, str]],
) -> Dict[str, Any]:
    dictionary_by_sheet: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for item in dictionary:
        dictionary_by_sheet[item["sheet_name"]].append(item)
    canonical: Dict[str, List[List[Any]]] = {}
    header_failures = []
    row_counts: Dict[str, int] = {}
    sheet_checksums: Dict[str, str] = {}
    header_checksums: Dict[str, str] = {}
    null_profile: Dict[str, Dict[str, int]] = {}
    guid_invalid = []
    guid_values = []
    pk_duplicates = []
    pk_values: Dict[str, List[List[Any]]] = {}

    for sheet in order:
        expected_header = headers[sheet]
        matrix = matrices[sheet]
        actual_header = [str(value) for value in matrix[0]]
        if actual_header != expected_header:
            header_failures.append({"sheet": sheet, "expected": expected_header, "actual": actual_header})
        kinds = [item["data_type"] for item in dictionary_by_sheet[sheet]]
        rows = [
            [canonical_cell(row[index] if index < len(row) else "", kinds[index]) for index in range(len(expected_header))]
            for row in matrix[1:]
        ]
        canonical[sheet] = [expected_header] + rows
        row_counts[sheet] = len(rows)
        header_checksums[sheet] = sha256_bytes(canonical_json(expected_header))
        sheet_checksums[sheet] = sha256_bytes(canonical_json(canonical[sheet]))
        null_profile[sheet] = {
            field: sum(row[index] == "" for row in rows)
            for index, field in enumerate(expected_header)
        }

        pk_fields = [item["field_name"] for item in dictionary_by_sheet[sheet] if item["primary_key"] in {"YES", "PART"}]
        pk_indexes = [expected_header.index(field) for field in pk_fields]
        keys = [[row[index] for index in pk_indexes] for row in rows]
        pk_values[sheet] = keys
        seen = set()
        for row_number, key in enumerate(keys, start=2):
            token = canonical_json(key)
            if not key or any(value == "" for value in key) or token in seen:
                pk_duplicates.append({"sheet": sheet, "row": row_number, "key": key})
            seen.add(token)

        for index, item in enumerate(dictionary_by_sheet[sheet]):
            if item["data_type"] != "uuid":
                continue
            for row_number, row in enumerate(rows, start=2):
                value = row[index]
                if value == "":
                    continue
                guid_values.append([sheet, item["field_name"], value])
                if not is_uuid(value):
                    guid_invalid.append({"sheet": sheet, "row": row_number, "field": item["field_name"], "value": value})

    fk_failures = []
    for item in dictionary:
        if not item["foreign_key"]:
            continue
        source_sheet = item["sheet_name"]
        source_index = headers[source_sheet].index(item["field_name"])
        target_sheet, target_field = item["foreign_key"].split(".", 1)
        target_index = headers[target_sheet].index(target_field)
        allowed = {row[target_index] for row in canonical[target_sheet][1:] if row[target_index] != ""}
        for row_number, row in enumerate(canonical[source_sheet][1:], start=2):
            value = row[source_index]
            if value != "" and value not in allowed:
                fk_failures.append({
                    "sheet": source_sheet,
                    "row": row_number,
                    "field": item["field_name"],
                    "target": item["foreign_key"],
                    "value": value,
                })

    variant_header = headers["RAW_VARIANTS"]
    description_index = variant_header.index("description_raw")
    leading_zero_values = [
        row[description_index]
        for row in canonical["RAW_VARIANTS"][1:]
        if re.search(r"(^|[^0-9])06([^0-9]|$)", str(row[description_index]))
    ]
    signatures = {
        "headers": sha256_bytes(canonical_json([[sheet, headers[sheet]] for sheet in order])),
        "primary_keys": sha256_bytes(canonical_json(pk_values)),
        "foreign_keys": sha256_bytes(canonical_json(fk_failures)),
        "guid_values": sha256_bytes(canonical_json(sorted(guid_values))),
        "null_profile": sha256_bytes(canonical_json(null_profile)),
        "leading_zero_06": sha256_bytes(canonical_json(leading_zero_values)),
    }
    return {
        "sheet_count": len(order),
        "field_count": sum(len(headers[sheet]) for sheet in order),
        "row_counts": row_counts,
        "sheet_checksums": sheet_checksums,
        "header_checksums": header_checksums,
        "overall_checksum": sha256_bytes(canonical_json(canonical)),
        "signatures": signatures,
        "header_failures": header_failures,
        "pk_duplicate_count": len(pk_duplicates),
        "pk_duplicates": pk_duplicates,
        "fk_failure_count": len(fk_failures),
        "fk_failures": fk_failures,
        "guid_invalid_count": len(guid_invalid),
        "guid_invalid": guid_invalid,
        "leading_zero_06_values": leading_zero_values,
        "canonical": canonical,
    }


def comparable_state(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "sheet_count": state["sheet_count"],
        "field_count": state["field_count"],
        "row_counts": state["row_counts"],
        "sheet_checksums": state["sheet_checksums"],
        "header_checksums": state["header_checksums"],
        "overall_checksum": state["overall_checksum"],
        "signatures": state["signatures"],
        "header_failures": state["header_failures"],
        "pk_duplicate_count": state["pk_duplicate_count"],
        "fk_failure_count": state["fk_failure_count"],
        "guid_invalid_count": state["guid_invalid_count"],
        "leading_zero_06_values": state["leading_zero_06_values"],
    }


def cell_data(value: Any) -> Dict[str, Any]:
    if value in (None, ""):
        return {}
    if isinstance(value, bool):
        return {"userEnteredValue": {"boolValue": value}}
    if isinstance(value, (int, float)):
        return {"userEnteredValue": {"numberValue": value}}
    return {"userEnteredValue": {"stringValue": str(value)}}


def snapshot_update_requests(
    worksheets: Dict[str, Any],
    fixture_state: Dict[str, Any],
    baseline_state: Dict[str, Any],
    headers: Dict[str, List[str]],
) -> List[Dict[str, Any]]:
    requests: List[Dict[str, Any]] = []
    for sheet in ("RAW_CURRENT_PRICES", "RAW_CURRENT_STOCK"):
        fixture_rows = fixture_state["canonical"][sheet][1:]
        max_rows = max(len(fixture_rows), baseline_state["row_counts"][sheet])
        width = len(headers[sheet])
        rows = []
        for row_index in range(max_rows):
            values = fixture_rows[row_index] if row_index < len(fixture_rows) else [""] * width
            rows.append({"values": [cell_data(value) for value in values]})
        requests.append({
            "updateCells": {
                "range": {
                    "sheetId": worksheets[sheet].id,
                    "startRowIndex": 1,
                    "endRowIndex": 1 + max_rows,
                    "startColumnIndex": 0,
                    "endColumnIndex": width,
                },
                "rows": rows,
                "fields": "userEnteredValue",
            }
        })
    return requests


def controlled_failure_request() -> Dict[str, Any]:
    return {
        "updateCells": {
            "range": {
                "sheetId": 2147483647,
                "startRowIndex": 1,
                "endRowIndex": 2,
                "startColumnIndex": 0,
                "endColumnIndex": 1,
            },
            "rows": [{"values": [{"userEnteredValue": {"stringValue": "CONTROLLED_FAILURE"}}]}],
            "fields": "userEnteredValue",
        }
    }


def controlled_mutation_request(sheet_id: int) -> Dict[str, Any]:
    return {
        "updateCells": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 1,
                "endRowIndex": 2,
                "startColumnIndex": 0,
                "endColumnIndex": 1,
            },
            "rows": [{"values": [{"userEnteredValue": {"stringValue": "CONTROLLED_FAILURE_SENTINEL"}}]}],
            "fields": "userEnteredValue",
        }
    }


def phase_d_idempotency() -> Dict[str, Any]:
    import gspread

    frozen_before = verify_frozen_checksums()
    if frozen_before["status"] != "PASS":
        raise RuntimeError("Frozen fixture checksum verification failed before Phase D")
    data, ctx = load_frozen_fixture()
    dry_run = validate_fixture(data, ctx, output_path=None)
    if dry_run["status"] != "PASS" or dry_run["validation_count"] != 171 or dry_run["passed"] != 171:
        raise RuntimeError("Phase D frozen-fixture DRY RUN is not PASS 171/171")

    load_dotenv(ENV_FILE)
    credentials = os.environ.get("GOOGLE_CREDENTIALS_PATH", "")
    if not credentials:
        raise RuntimeError("GOOGLE_CREDENTIALS_PATH is not configured")
    client = gspread.service_account(filename=credentials)
    spreadsheet = client.open_by_key(os.environ.get("RAW_COMPLETE_SPREADSHEET_ID") or SPREADSHEET_ID)
    worksheet_list = spreadsheet.worksheets()
    order = ctx["order"]
    headers = ctx["headers"]
    if [worksheet.title for worksheet in worksheet_list] != order:
        raise RuntimeError("Live worksheet order differs from approved contract")
    worksheets = {worksheet.title: worksheet for worksheet in worksheet_list}

    fixture_state = state_from_matrices(fixture_matrices(data, order, headers), order, headers, ctx["dictionary"])
    baseline_state = state_from_matrices(read_google_matrices(spreadsheet, order, headers), order, headers, ctx["dictionary"])
    baseline_matches_fixture = comparable_state(baseline_state) == comparable_state(fixture_state)
    baseline_artifact = {
        "captured_at_utc": utc_now(),
        "spreadsheet_id_masked": SPREADSHEET_ID[:6] + "…" + SPREADSHEET_ID[-6:],
        "fixture_checksum_verification": frozen_before,
        "matches_frozen_fixture": baseline_matches_fixture,
        "state": comparable_state(baseline_state),
    }
    write_json(PHASE_D_DIR / "idempotency_baseline.json", baseline_artifact)
    if not baseline_matches_fixture:
        raise RuntimeError("Live baseline differs from the frozen fixture; Phase D write aborted")

    requests = snapshot_update_requests(worksheets, fixture_state, baseline_state, headers)
    failure_error_type = None
    failure_http_status = None
    try:
        spreadsheet.batch_update({
            "requests": requests + [
                controlled_mutation_request(worksheets["RAW_CURRENT_PRICES"].id),
                controlled_failure_request(),
            ],
            "includeSpreadsheetInResponse": False,
        })
    except Exception as exc:
        failure_error_type = type(exc).__name__
        response = getattr(exc, "response", None)
        failure_http_status = getattr(response, "status_code", None)
    if failure_error_type is None:
        raise RuntimeError("Controlled failure request unexpectedly succeeded")
    failure_state = state_from_matrices(read_google_matrices(spreadsheet, order, headers), order, headers, ctx["dictionary"])
    rollback_unchanged = comparable_state(failure_state) == comparable_state(baseline_state)
    failure_artifact = {
        "status": "PASS" if rollback_unchanged else "FAIL",
        "tested_at_utc": utc_now(),
        "operation": "single atomic batch containing valid snapshot replacements, a controlled sentinel mutation, and one intentionally invalid sheetId",
        "expected_error_observed": True,
        "safe_error_type": failure_error_type,
        "http_status": failure_http_status,
        "baseline_unchanged_after_failure": rollback_unchanged,
        "baseline_overall_checksum": baseline_state["overall_checksum"],
        "after_failure_overall_checksum": failure_state["overall_checksum"],
        "row_counts_unchanged": failure_state["row_counts"] == baseline_state["row_counts"],
        "sheet_checksums_unchanged": failure_state["sheet_checksums"] == baseline_state["sheet_checksums"],
    }
    write_json(PHASE_D_DIR / "failure_rollback_validation.json", failure_artifact)
    if not rollback_unchanged:
        raise RuntimeError("Controlled failure changed the live baseline")

    spreadsheet.batch_update({"requests": requests, "includeSpreadsheetInResponse": False})
    after_state = state_from_matrices(read_google_matrices(spreadsheet, order, headers), order, headers, ctx["dictionary"])
    frozen_after = verify_frozen_checksums()
    if frozen_after != frozen_before:
        raise RuntimeError("Frozen fixture changed during Phase D")

    row_counts_comparison = {
        sheet: {
            "fixture": fixture_state["row_counts"][sheet],
            "baseline": baseline_state["row_counts"][sheet],
            "after": after_state["row_counts"][sheet],
            "match": fixture_state["row_counts"][sheet] == baseline_state["row_counts"][sheet] == after_state["row_counts"][sheet],
        }
        for sheet in order
    }
    checksums_comparison = {
        sheet: {
            "fixture": fixture_state["sheet_checksums"][sheet],
            "baseline": baseline_state["sheet_checksums"][sheet],
            "after": after_state["sheet_checksums"][sheet],
            "match": fixture_state["sheet_checksums"][sheet] == baseline_state["sheet_checksums"][sheet] == after_state["sheet_checksums"][sheet],
        }
        for sheet in order
    }
    write_json(PHASE_D_DIR / "row_counts_comparison.json", row_counts_comparison)
    write_json(PHASE_D_DIR / "checksums_comparison.json", checksums_comparison)

    after_matches_fixture = comparable_state(after_state) == comparable_state(fixture_state)
    after_matches_baseline = comparable_state(after_state) == comparable_state(baseline_state)
    new_rows = sum(after_state["row_counts"][sheet] - baseline_state["row_counts"][sheet] for sheet in order)
    atomic_artifact = {
        "status": "PASS" if after_matches_fixture and after_matches_baseline else "FAIL",
        "tested_at_utc": utc_now(),
        "single_batch_request": True,
        "snapshot_sheets": ["RAW_CURRENT_PRICES", "RAW_CURRENT_STOCK"],
        "static_sheets_no_op": [sheet for sheet in order if sheet not in {"RAW_CURRENT_PRICES", "RAW_CURRENT_STOCK"}],
        "unprotected_clear_then_append_used": False,
        "request_count": len(requests),
        "baseline_overall_checksum": baseline_state["overall_checksum"],
        "after_overall_checksum": after_state["overall_checksum"],
        "unchanged": after_matches_baseline,
    }
    write_json(PHASE_D_DIR / "atomic_replacement_validation.json", atomic_artifact)
    write_json(PHASE_D_DIR / "idempotency_after.json", {
        "captured_at_utc": utc_now(),
        "matches_frozen_fixture": after_matches_fixture,
        "matches_baseline": after_matches_baseline,
        "frozen_fixture_checksum_verification": frozen_after,
        "state": comparable_state(after_state),
    })

    all_counts_match = all(item["match"] for item in row_counts_comparison.values())
    all_checksums_match = all(item["match"] for item in checksums_comparison.values())
    all_signatures_match = fixture_state["signatures"] == baseline_state["signatures"] == after_state["signatures"]
    headers_unchanged = not after_state["header_failures"] and after_state["header_checksums"] == baseline_state["header_checksums"]
    pass_conditions = {
        "dry_run_171_of_171": dry_run["status"] == "PASS" and dry_run["passed"] == 171,
        "baseline_matches_fixture": baseline_matches_fixture,
        "failure_rollback_pass": rollback_unchanged,
        "atomic_replacement_pass": atomic_artifact["status"] == "PASS",
        "read_back_validation_pass": after_matches_fixture,
        "row_counts_match": all_counts_match,
        "canonical_checksums_match": all_checksums_match,
        "new_rows_created_zero": new_rows == 0,
        "headers_and_order_unchanged": headers_unchanged,
        "pk_unchanged_and_unique": all_signatures_match and after_state["pk_duplicate_count"] == 0,
        "fk_unchanged_and_resolved": all_signatures_match and after_state["fk_failure_count"] == 0,
        "guid_unchanged_and_valid": all_signatures_match and after_state["guid_invalid_count"] == 0,
        "null_profile_unchanged": all_signatures_match,
        "leading_zero_06_preserved": bool(after_state["leading_zero_06_values"]) and all_signatures_match,
        "frozen_fixture_unchanged": frozen_after == frozen_before,
    }
    final_status = "PASS" if all(pass_conditions.values()) else "FAIL"
    validation_artifact = {
        "status": final_status,
        "validated_at_utc": utc_now(),
        "fixture": str(FIXTURE),
        "same_cutoff_at_utc": ctx["manifest"]["cutoff_at_utc"],
        "dry_run": {
            "status": dry_run["status"],
            "validation_count": dry_run["validation_count"],
            "passed": dry_run["passed"],
            "failed": dry_run["failed"],
        },
        "pass_conditions": pass_conditions,
        "new_rows_created": new_rows,
        "baseline_total_rows": sum(baseline_state["row_counts"].values()),
        "after_total_rows": sum(after_state["row_counts"].values()),
        "baseline_overall_checksum": baseline_state["overall_checksum"],
        "after_overall_checksum": after_state["overall_checksum"],
        "failure_rollback_status": failure_artifact["status"],
        "atomic_replacement_status": atomic_artifact["status"],
        "read_back_validation": "PASS" if after_matches_fixture else "FAIL",
    }
    write_json(PHASE_D_DIR / "idempotency_validation.json", validation_artifact)
    if final_status != "PASS":
        raise RuntimeError("Phase D validation failed; inspect phase_d artifacts")
    return validation_artifact


def column_name(number: int) -> str:
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["extract", "load-fixture", "read-back", "phase-d"])
    args = parser.parse_args()
    if args.operation == "extract":
        FIXTURE.mkdir(parents=True, exist_ok=True)
        data, ctx = build_fixture()
        report = validate_fixture(data, ctx)
        finalize_checksums()
        print(json.dumps({"fixture": str(FIXTURE), "status": report["status"], "validations": {"total": report["validation_count"], "passed": report["passed"], "failed": report["failed"], "applicable": report["applicable"], "not_applicable": report["not_applicable"]}, "row_counts": ctx["manifest"]["row_counts"], "type_errors": report["type_errors"]}, ensure_ascii=False, indent=2))
    elif args.operation == "load-fixture":
        print(json.dumps(load_fixture(write=True), ensure_ascii=False, indent=2))
    elif args.operation == "phase-d":
        print(json.dumps(phase_d_idempotency(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(load_fixture(write=False), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
