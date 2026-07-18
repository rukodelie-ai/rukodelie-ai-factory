#!/usr/bin/env python3
"""E1 Phase 1 full extraction, validation, atomic load and read-back.

All 1C access is read-only.  The approved Google Sheets target is not changed
until a complete shadow copy has passed validation.  The final server-side
copy from shadow sheets to the 32 approved sheet IDs is one atomic batch.
"""

import argparse
import base64
import csv
import datetime as dt
import gc
import hashlib
import importlib.util
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from dotenv import load_dotenv


PROJECT = Path("/Users/sergey/Library/Mobile Documents/com~apple~CloudDocs/RUKODELIE_AI_FACTORY")
CONTRACT = PROJECT / "09_DOCUMENTS" / "RAW_COMPLETE_V1_CONTRACT"
BASE_SCRIPT = CONTRACT / "TEST_EXTRACTION_FIXTURE" / "raw_complete_v1_test_extraction.py"
E1_ROOT = CONTRACT / "E1_PHASE_1_FULL"
SNAPSHOT = E1_ROOT / "yarn_204_9114"
RAW_DIR = SNAPSHOT / "raw"
NORMALIZED_DIR = SNAPSHOT / "normalized"
ENV_FILE = PROJECT / "03_TELEGRAM" / ".env"
PRODUCT_SCOPE_CSV = PROJECT / "02_PRODUCT_DATABASE" / "MASTER_PRODUCT_DATABASE_RAW_YARN_V1.csv"
VARIANT_SCOPE_CSV = PROJECT / "02_PRODUCT_DATABASE" / "AI_PRODUCT_KNOWLEDGE_YARN_V1.csv"
WAREHOUSE_MAP_JSON = PROJECT / "02_PRODUCT_DATABASE" / "phase2_artifacts" / "phase2_warehouses.json"
PRICE_TYPE_MAP_JSON = PROJECT / "02_PRODUCT_DATABASE" / "phase2_artifacts" / "phase2_price_types.json"
SOURCE_SYSTEM_ID = "1C_STANDARD_ODATA"
SCHEMA_VERSION_ID = "RAW_COMPLETE_V1"
EXTRACTOR_VERSION = "raw-complete-v1-e1-full/1.0"
ZERO_GUID = "00000000-0000-0000-0000-000000000000"
VARIANT_FILE_TYPE = "StandardODATA.Catalog_iq_ИзображенияХарактеристикПрисоединенныеФайлы"
PRODUCT_FILE_TYPE = "StandardODATA.Catalog_НоменклатураПрисоединенныеФайлы"
STAGE_PREFIX = "__E1_STAGE_"
MAX_VALUES_PAYLOAD = 1_500_000
GOOGLE_HTTP_TIMEOUT = (10, 90)
GOOGLE_READ_PACING_SECONDS = 1.1
GOOGLE_WRITE_PACING_SECONDS = 1.2
GOOGLE_QUOTA_RESET_SECONDS = 65
GUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

APPROVED_PRICE_TYPE_NAMES = {
    "Акция -10%",
    "Интернет-магазин",
    "Приходная",
    "Оптовая",
    "Розничная",
    "Цена Kaspi",
    "Цена Kaspi ТОО",
    "Halyk Market",
    "Цены OZON (RUB)",
    "Цены OZON до применения скидки (RUB)",
}


def load_base_module() -> Any:
    spec = importlib.util.spec_from_file_location("raw_complete_fixture", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load approved fixture implementation")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE = load_base_module()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(str(temporary), str(path))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def chunks(values: Sequence[str], size: int) -> Iterable[List[str]]:
    for index in range(0, len(values), size):
        yield list(values[index:index + size])


def safe_label(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")


def sorted_source_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(rows, key=canonical_json)


def source_record_hash(row: Dict[str, Any]) -> str:
    return sha256_bytes(canonical_json(row))


class ReadOnlyODataClient(BASE.ODataClient):
    def _get_json(self, url: str, timeout: int = 120) -> Any:
        request = urllib.request.Request(url, headers=self.headers, method="GET")
        last_error: Optional[Exception] = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    return json.loads(response.read().decode("utf-8-sig"))
            except urllib.error.HTTPError as exc:
                last_error = exc
                safe_body = exc.read(500).decode("utf-8", errors="replace").replace("\n", " ")
                if exc.code not in {408, 429, 500, 502, 503, 504} or attempt == 3:
                    raise RuntimeError("Read-only OData HTTP %d: %s" % (exc.code, safe_body[:500]))
                time.sleep(2 ** attempt)
            except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
                last_error = exc
                if attempt == 3:
                    break
                time.sleep(2 ** attempt)
        raise RuntimeError("Read-only OData GET failed after bounded retries: %s" % type(last_error).__name__)


class RunRegistry:
    def __init__(self, headers: Dict[str, List[str]], started: str, cutoff: str) -> None:
        self.headers = headers
        self.started = started
        self.cutoff = cutoff
        self.items: Dict[str, Dict[str, Any]] = {}

    def run_id(self, entity: str) -> str:
        compact = re.sub(r"[^A-Za-z0-9]+", "_", entity).strip("_")
        prefix = "e1_" + self.started.replace("-", "").replace(":", "")
        return (prefix + "_" + compact)[:150] + "_" + sha256_bytes(entity.encode("utf-8"))[:10]

    def register(self, entity: str, selected: Sequence[str], scope: str) -> str:
        if entity not in self.items:
            row = BASE.make_row(self.headers["RAW_EXTRACTION_RUNS"])
            row.update({
                "run_id": self.run_id(entity),
                "schema_version_id": SCHEMA_VERSION_ID,
                "source_system_id": SOURCE_SYSTEM_ID,
                "source_entityset": entity,
                "started_at_utc": self.started,
                "scope_filter_masked": scope,
                "selected_fields": ",".join(selected),
                "extractor_version": EXTRACTOR_VERSION,
                "status": "STARTED",
                "extracted_count": 0,
                "validated_count": 0,
                "rejected_count": 0,
                "missing_relation_count": 0,
            })
            self.items[entity] = row
        else:
            current = set(filter(None, str(self.items[entity].get("selected_fields") or "").split(",")))
            current.update(selected)
            self.items[entity]["selected_fields"] = ",".join(sorted(current))
        return self.run_id(entity)

    def add_count(self, entity: str, count: int) -> None:
        self.items[entity]["extracted_count"] = int(self.items[entity].get("extracted_count") or 0) + count

    def add_missing(self, entity: str, count: int) -> None:
        self.items[entity]["missing_relation_count"] = int(self.items[entity].get("missing_relation_count") or 0) + count

    def finalize(self, data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        rows = []
        for entity, row in self.items.items():
            row["finished_at_utc"] = utc_now()
            row["status"] = "SUCCESS"
            row["expected_count"] = row["extracted_count"]
            row["validated_count"] = row["extracted_count"]
            row["rejected_count"] = 0
            related = [item for values in data.values() for item in values if str(item.get("source_entityset") or "") == entity]
            row["content_checksum_sha256"] = sha256_bytes(canonical_json(related))
            rows.append(row)
        return sorted(rows, key=lambda item: str(item["run_id"]))


def scope_data() -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    with PRODUCT_SCOPE_CSV.open(encoding="utf-8-sig", newline="") as handle:
        products = list(csv.DictReader(handle))
    with VARIANT_SCOPE_CSV.open(encoding="utf-8-sig", newline="") as handle:
        variants = list(csv.DictReader(handle))
    if len(products) != 204 or len({row["ref_key"].lower() for row in products}) != 204:
        raise RuntimeError("Approved product scope seed is not 204 unique products")
    if len(variants) != 9114 or len({row["characteristic_key"].lower() for row in variants}) != 9114:
        raise RuntimeError("Approved variant scope seed is not 9,114 unique variants")
    if len({row["ref_key"].lower() for row in variants}) != 204:
        raise RuntimeError("Variant scope does not close over 204 approved products")
    return products, variants


def run_context() -> Dict[str, Any]:
    path = SNAPSHOT / "run_context.json"
    if path.is_file():
        value = read_json(path)
        if value.get("scope") != {"products": 204, "variants": 9114}:
            raise RuntimeError("Existing E1 checkpoint has a different scope")
        return value
    started = utc_now()
    value = {
        "run_id": "e1_yarn_204_9114_" + started.replace("-", "").replace(":", ""),
        "started_at_utc": started,
        "cutoff_at_utc": started,
        "scope": {"products": 204, "variants": 9114},
        "source_access": "READ_ONLY",
        "extractor_version": EXTRACTOR_VERSION,
    }
    atomic_json(path, value)
    return value


def checkpoint_path(label: str, index: int) -> Path:
    return RAW_DIR / safe_label(label) / ("batch_%04d.json" % (index + 1))


def checkpoint_query(
    client: ReadOnlyODataClient,
    label: str,
    index: int,
    entity: str,
    params: Dict[str, str],
    scope_ids: Sequence[str],
) -> Path:
    path = checkpoint_path(label, index)
    descriptor = {"entity": entity, "params": params, "scope_ids": list(scope_ids)}
    request_checksum = sha256_bytes(canonical_json(descriptor))
    if path.is_file():
        payload = read_json(path)
        if payload.get("request_checksum_sha256") != request_checksum:
            raise RuntimeError("Checkpoint request mismatch: " + str(path))
        return path
    rows = sorted_source_rows(client.query(entity, params))
    atomic_json(path, {
        "entity": entity,
        "request_checksum_sha256": request_checksum,
        "scope_ids": list(scope_ids),
        "row_count": len(rows),
        "rows": rows,
    })
    return path


def query_scoped_batches(
    client: ReadOnlyODataClient,
    label: str,
    entity: str,
    scope_ids: Sequence[str],
    filter_field: str,
    selected: Sequence[str],
    batch_size: int = 8,
    extra_filter: Optional[str] = None,
    workers: int = 4,
) -> List[Path]:
    batches = list(chunks(list(scope_ids), batch_size))
    results: List[Optional[Path]] = [None] * len(batches)

    def work(index: int, ids: List[str]) -> Tuple[int, Path]:
        where = "(" + BASE.guid_filter(filter_field, ids) + ")"
        if extra_filter:
            where = where + " and " + extra_filter
        params = {"$filter": where, "$select": ",".join(selected), "$format": "json"}
        return index, checkpoint_query(client, label, index, entity, params, ids)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(work, index, ids) for index, ids in enumerate(batches)]
        completed = 0
        for future in as_completed(futures):
            index, path = future.result()
            results[index] = path
            completed += 1
            if completed % 25 == 0 or completed == len(batches):
                print("%s: %d/%d batches" % (label, completed, len(batches)), flush=True)
    return [path for path in results if path is not None]


def query_exact_wide_batches(
    client: ReadOnlyODataClient,
    label: str,
    entity: str,
    ids: Sequence[str],
    selected: Sequence[str],
    batch_size: int = 8,
    workers: int = 4,
) -> List[Path]:
    id_batches = list(chunks(list(ids), batch_size))
    selected_chunks = list(chunks(list(selected), 12))
    results: List[Optional[Path]] = [None] * len(id_batches)

    def work(index: int, batch_ids: List[str]) -> Tuple[int, Path]:
        path = checkpoint_path(label, index)
        descriptor = {"entity": entity, "ids": batch_ids, "selected": list(selected)}
        request_checksum = sha256_bytes(canonical_json(descriptor))
        if path.is_file():
            payload = read_json(path)
            if payload.get("request_checksum_sha256") != request_checksum:
                raise RuntimeError("Checkpoint request mismatch: " + str(path))
            return index, path
        merged: Dict[str, Dict[str, Any]] = {}
        where = "(" + BASE.guid_filter("Ref_Key", batch_ids) + ")"
        for field_chunk in selected_chunks:
            fields = list(dict.fromkeys((["Ref_Key"] if "Ref_Key" not in field_chunk else []) + field_chunk))
            rows = client.query(entity, {"$filter": where, "$select": ",".join(fields), "$format": "json"})
            for row in rows:
                merged.setdefault(str(row.get("Ref_Key") or "").lower(), {}).update(row)
        rows = sorted_source_rows(list(merged.values()))
        atomic_json(path, {
            "entity": entity,
            "request_checksum_sha256": request_checksum,
            "scope_ids": batch_ids,
            "row_count": len(rows),
            "rows": rows,
        })
        return index, path

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(work, index, batch_ids) for index, batch_ids in enumerate(id_batches)]
        completed = 0
        for future in as_completed(futures):
            index, path = future.result()
            results[index] = path
            completed += 1
            if completed % 25 == 0 or completed == len(id_batches):
                print("%s: %d/%d batches" % (label, completed, len(id_batches)), flush=True)
    return [path for path in results if path is not None]


def iter_checkpoint_rows(paths: Sequence[Path]) -> Iterable[Tuple[Dict[str, Any], List[str]]]:
    for path in paths:
        payload = read_json(path)
        scope_ids = [str(value).lower() for value in payload.get("scope_ids", [])]
        for row in payload.get("rows", []):
            yield row, scope_ids


def checkpoint_count(paths: Sequence[Path]) -> int:
    return sum(int(read_json(path).get("row_count") or 0) for path in paths)


def exact_closure(
    client: ReadOnlyODataClient,
    label: str,
    entity: str,
    initial_ids: Sequence[str],
    selected: Sequence[str],
    parent_field: Optional[str] = None,
) -> List[Dict[str, Any]]:
    wanted = {str(value).lower() for value in initial_ids if value and str(value).lower() != ZERO_GUID}
    found: Dict[str, Dict[str, Any]] = {}
    level = 0
    while wanted - set(found):
        missing = sorted(wanted - set(found))
        paths = query_scoped_batches(client, label + "_level_%02d" % level, entity, missing, "Ref_Key", selected, batch_size=10, workers=4)
        rows = [row for row, _ in iter_checkpoint_rows(paths)]
        for row in rows:
            key = str(row.get("Ref_Key") or "").lower()
            if key:
                found[key] = row
                if parent_field:
                    parent = str(row.get(parent_field) or "").lower()
                    if parent and parent != ZERO_GUID:
                        wanted.add(parent)
        level += 1
        if level > 20:
            raise RuntimeError("Closure traversal exceeded 20 levels for " + entity)
    if set(found) != wanted:
        raise RuntimeError("Referenced closure is incomplete for " + entity)
    return [found[key] for key in sorted(found)]


def add_provenance(row: Dict[str, Any], entity: str, record_id: str, registry: RunRegistry) -> None:
    BASE.add_provenance(row, entity, record_id, registry.run_id(entity))


def description_row(
    headers: Dict[str, List[str]],
    owner_id: str,
    description_type: str,
    content_format: str,
    content: Any,
    deletion_mark: Any,
    entity: str,
    record_id: str,
    registry: RunRegistry,
) -> Dict[str, Any]:
    text = "" if content is None else str(content)
    if len(text) > 50000:
        raise RuntimeError("Description exceeds Google Sheets 50,000 character cell limit")
    row = BASE.make_row(headers["RAW_DESCRIPTIONS"])
    row.update({
        "description_id": owner_id + "|" + description_type + "|" + record_id,
        "owner_type": "PRODUCT",
        "owner_id": owner_id,
        "description_type": description_type,
        "language_code": "und",
        "content_format": content_format,
        "content_raw": text,
        "content_length": len(text),
        "content_sha256": sha256_bytes(text.encode("utf-8")),
        "deletion_mark": deletion_mark,
    })
    add_provenance(row, entity, record_id, registry)
    return row


def binary_checkpoint_group(
    client: ReadOnlyODataClient,
    index: int,
    requests: Sequence[Tuple[str, str]],
) -> Path:
    label = "InformationRegister_ДвоичныеДанныеФайлов"
    path = checkpoint_path(label, index)
    descriptor = {"entity": label, "requests": list(requests), "mode": "direct-composite-key-base64-once"}
    request_checksum = sha256_bytes(canonical_json(descriptor))
    if path.is_file():
        payload = read_json(path)
        if payload.get("request_checksum_sha256") != request_checksum:
            raise RuntimeError("Binary checkpoint request mismatch: " + str(path))
        return path
    rows = []
    selected = ["Файл", "Файл_Type", "ДвоичныеДанныеФайла_Type", "ДвоичныеДанныеФайла_Base64Data"]
    for file_id, file_type in requests:
        key = "%s(Файл='%s',Файл_Type='%s')" % (label, file_id, file_type)
        source = client.direct(key, selected)
        encoded_raw = source.get("ДвоичныеДанныеФайла_Base64Data") or ""
        encoded = "".join(str(encoded_raw).lstrip("\ufeff").strip().strip("\"").split())
        try:
            decoded = base64.b64decode(encoded, validate=True) if encoded else b""
        except Exception as exc:
            raise RuntimeError("Invalid Base64 for masked file %s…%s" % (file_id[:6], file_id[-4:])) from exc
        mime = None
        if decoded.startswith(b"\xff\xd8\xff"):
            mime = "image/jpeg"
        elif decoded.startswith(b"\x89PNG\r\n\x1a\n"):
            mime = "image/png"
        rows.append({
            "file_id": file_id,
            "file_type_raw": source.get("Файл_Type"),
            "binary_value_type_raw": source.get("ДвоичныеДанныеФайла_Type"),
            "payload_present": bool(decoded),
            "payload_base64_length": len(encoded) if encoded else None,
            "decoded_size_bytes": len(decoded) if decoded else None,
            "mime_type_detected": mime,
            "content_hash_sha256": sha256_bytes(decoded) if decoded else None,
        })
    atomic_json(path, {
        "entity": label,
        "request_checksum_sha256": request_checksum,
        "row_count": len(rows),
        "rows": rows,
        "binary_payload_persisted": False,
    })
    return path


def extract_binary_metadata(
    client: ReadOnlyODataClient,
    requests: Sequence[Tuple[str, str]],
    headers: Dict[str, List[str]],
    registry: RunRegistry,
    cutoff: str,
) -> List[Dict[str, Any]]:
    grouped = list(chunks([file_id + "\t" + file_type for file_id, file_type in requests], 20))
    result_paths: List[Optional[Path]] = [None] * len(grouped)

    def work(index: int, group: Sequence[str]) -> Tuple[int, Path]:
        parsed = [tuple(value.split("\t", 1)) for value in group]
        return index, binary_checkpoint_group(client, index, parsed)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(work, index, group) for index, group in enumerate(grouped)]
        completed = 0
        for future in as_completed(futures):
            index, path = future.result()
            result_paths[index] = path
            completed += 1
            if completed % 25 == 0 or completed == len(grouped):
                print("binary metadata: %d/%d groups" % (completed, len(grouped)), flush=True)
    rows = []
    for path in result_paths:
        if path is None:
            continue
        for source in read_json(path).get("rows", []):
            file_id = str(source["file_id"]).lower()
            file_type = str(source["file_type_raw"])
            storage_id = BASE.binary_key(file_id, file_type)
            row = BASE.make_row(headers["RAW_BINARY_STORAGE_METADATA"])
            row.update({
                "binary_storage_id": storage_id,
                "file_id": file_id,
                "file_type_raw": file_type,
                "binary_value_type_raw": source.get("binary_value_type_raw"),
                "payload_present": bool(source.get("payload_present")),
                "payload_base64_length": source.get("payload_base64_length"),
                "decoded_size_bytes": source.get("decoded_size_bytes"),
                "mime_type_detected": source.get("mime_type_detected"),
                "content_hash_sha256": source.get("content_hash_sha256"),
                "retrieval_method": "ODATA_DIRECT_COMPOSITE_KEY_BASE64_ONCE",
                "last_verified_at_utc": cutoff,
            })
            add_provenance(row, "InformationRegister_ДвоичныеДанныеФайлов", storage_id, registry)
            rows.append(row)
    return rows


def write_normalized(
    data: Dict[str, List[Dict[str, Any]]],
    order: Sequence[str],
    headers: Dict[str, List[str]],
    dictionary: List[Dict[str, str]],
) -> None:
    by_sheet: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for item in dictionary:
        by_sheet[item["sheet_name"]].append(item)
    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)
    for sheet in order:
        pk = [item["field_name"] for item in by_sheet[sheet] if item["primary_key"] in {"YES", "PART"}]
        data[sheet].sort(key=lambda row: tuple(str(row.get(field) or "") for field in pk))
        path = NORMALIZED_DIR / (sheet + ".csv")
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers[sheet], extrasaction="raise")
            writer.writeheader()
            for row in data[sheet]:
                writer.writerow({field: "" if row.get(field) is None else row.get(field) for field in headers[sheet]})


def extraction_preflight(save: bool = True) -> Dict[str, Any]:
    import gspread

    load_dotenv(ENV_FILE)
    required_env = ["RAW_COMPLETE_SPREADSHEET_ID", "GOOGLE_CREDENTIALS_PATH", "ODATA_BASE_URL", "ODATA_USERNAME", "ODATA_PASSWORD"]
    missing_env = [name for name in required_env if not os.environ.get(name)]
    required_files = [
        CONTRACT / "RAW_COMPLETE_V1_DATA_DICTIONARY.csv",
        CONTRACT / "RAW_COMPLETE_V1_ENTITYSET_MAPPING.csv",
        CONTRACT / "RAW_COMPLETE_V1_VALIDATION_MATRIX.csv",
        CONTRACT / "RAW_COMPLETE_V1_IMPORT_PLAN.md",
        BASE_SCRIPT,
        PRODUCT_SCOPE_CSV,
        VARIANT_SCOPE_CSV,
        WAREHOUSE_MAP_JSON,
        PRICE_TYPE_MAP_JSON,
    ]
    missing_files = [str(path) for path in required_files if not path.is_file()]
    if missing_env or missing_files:
        raise RuntimeError("E1 preflight configuration is incomplete")
    products, variants = scope_data()
    dictionary = BASE.read_csv(CONTRACT / "RAW_COMPLETE_V1_DATA_DICTIONARY.csv")
    mappings = BASE.read_csv(CONTRACT / "RAW_COMPLETE_V1_ENTITYSET_MAPPING.csv")
    matrix = BASE.read_csv(CONTRACT / "RAW_COMPLETE_V1_VALIDATION_MATRIX.csv")
    order, headers = BASE.get_headers(dictionary)
    client = gspread.service_account(filename=os.environ["GOOGLE_CREDENTIALS_PATH"])
    spreadsheet = client.open_by_key(os.environ["RAW_COMPLETE_SPREADSHEET_ID"])
    worksheets = spreadsheet.worksheets()
    matrices = BASE.read_google_matrices(spreadsheet, order, headers)
    state = BASE.state_from_matrices(matrices, order, headers, dictionary)
    odata = ReadOnlyODataClient()
    probe = odata.query("Catalog_Номенклатура", {
        "$filter": "Ref_Key eq guid'f5f42c43-0da6-11ea-80cb-9633c5df92df'",
        "$select": "Ref_Key,Code",
        "$format": "json",
    })
    result = {
        "status": "PASS" if (
            len(order) == 32
            and sum(len(headers[sheet]) for sheet in order) == 466
            and len(mappings) == 38
            and len(matrix) == 171
            and [worksheet.title for worksheet in worksheets] == order
            and not state["header_failures"]
            and len(products) == 204
            and len(variants) == 9114
            and len(probe) == 1
        ) else "FAIL",
        "captured_at_utc": utc_now(),
        "configuration": {name: True for name in required_env},
        "contract": {"sheets": len(order), "fields": sum(len(headers[sheet]) for sheet in order), "mappings": len(mappings), "validations": len(matrix)},
        "scope": {"products": len(products), "variants": len(variants)},
        "google_baseline": {
            "sheet_order": order,
            "row_counts": state["row_counts"],
            "sheet_checksums": state["sheet_checksums"],
            "header_checksums": state["header_checksums"],
            "overall_checksum": state["overall_checksum"],
            "total_rows": sum(state["row_counts"].values()),
        },
        "odata_read_only_probe": {"rows": len(probe), "matched": len(probe) == 1},
        "spreadsheet_id_masked": os.environ["RAW_COMPLETE_SPREADSHEET_ID"][:6] + "…" + os.environ["RAW_COMPLETE_SPREADSHEET_ID"][-6:],
    }
    if save:
        atomic_json(E1_ROOT / "preflight_baseline.json", result)
    if result["status"] != "PASS":
        raise RuntimeError("E1 preflight failed")
    return result


def build_e1_snapshot() -> Dict[str, Any]:
    products_seed, variants_seed = scope_data()
    product_ids = sorted({row["ref_key"].lower() for row in products_seed})
    variant_ids = sorted({row["characteristic_key"].lower() for row in variants_seed})
    variant_product = {row["characteristic_key"].lower(): row["ref_key"].lower() for row in variants_seed}
    variants_by_product: Dict[str, List[str]] = defaultdict(list)
    for variant_id, product_id in variant_product.items():
        variants_by_product[product_id].append(variant_id)
    for product_id in variants_by_product:
        variants_by_product[product_id].sort()

    dictionary = BASE.read_csv(CONTRACT / "RAW_COMPLETE_V1_DATA_DICTIONARY.csv")
    mappings = BASE.read_csv(CONTRACT / "RAW_COMPLETE_V1_ENTITYSET_MAPPING.csv")
    matrix = BASE.read_csv(CONTRACT / "RAW_COMPLETE_V1_VALIDATION_MATRIX.csv")
    order, headers = BASE.get_headers(dictionary)
    if len(order) != 32 or sum(len(headers[sheet]) for sheet in order) != 466 or len(mappings) != 38 or len(matrix) != 171:
        raise RuntimeError("Approved contract cardinality mismatch")
    context = run_context()
    started = context["started_at_utc"]
    cutoff = context["cutoff_at_utc"]
    client = ReadOnlyODataClient()
    registry = RunRegistry(headers, started, cutoff)
    data: Dict[str, List[Dict[str, Any]]] = {sheet: [] for sheet in order}
    source_exclusions: Dict[str, Any] = {}
    source_counts: Dict[str, int] = {}

    print("E1 extraction: products", flush=True)
    product_entity = "Catalog_Номенклатура"
    product_selected = list(dict.fromkeys(BASE.direct_source_properties(dictionary, "RAW_PRODUCTS", product_entity) + ["Описание"]))
    registry.register(product_entity, product_selected, "204 approved yarn product GUIDs")
    product_paths = query_exact_wide_batches(client, "products", product_entity, product_ids, product_selected, batch_size=8, workers=4)
    product_sources = {str(row.get("Ref_Key") or "").lower(): row for row, _ in iter_checkpoint_rows(product_paths)}
    registry.add_count(product_entity, checkpoint_count(product_paths))
    source_counts[product_entity] = checkpoint_count(product_paths)
    if set(product_sources) != set(product_ids):
        raise RuntimeError("Live 1C product scope is not exactly 204 approved GUIDs")
    seed_codes = {row["ref_key"].lower(): row["code_1c"] for row in products_seed}
    for product_id in product_ids:
        source = product_sources[product_id]
        if str(source.get("Code") or "").strip() != str(seed_codes[product_id]).strip():
            raise RuntimeError("Live product code mismatch for masked GUID %s…%s" % (product_id[:6], product_id[-4:]))
        row = BASE.map_direct(headers["RAW_PRODUCTS"], dictionary, "RAW_PRODUCTS", source)
        row["product_id"] = product_id
        parent_id = str(source.get("Parent_Key") or "").lower()
        row["parent_classification_id"] = "1C_GROUP:" + parent_id if parent_id and parent_id != ZERO_GUID else None
        add_provenance(row, product_entity, product_id, registry)
        data["RAW_PRODUCTS"].append(row)
        data["RAW_DESCRIPTIONS"].append(description_row(
            headers,
            product_id,
            "DIRECT_1C",
            "TEXT",
            source.get("Описание"),
            source.get("DeletionMark"),
            product_entity,
            product_id + "|DIRECT_1C",
            registry,
        ))

    print("E1 extraction: 9,114 variants", flush=True)
    variant_entity = "Catalog_ХарактеристикиНоменклатуры"
    variant_selected = BASE.direct_source_properties(dictionary, "RAW_VARIANTS", variant_entity)
    registry.register(variant_entity, variant_selected, "9,114 approved variant GUIDs")
    variant_paths = query_scoped_batches(client, "variants", variant_entity, variant_ids, "Ref_Key", variant_selected, batch_size=12, workers=6)
    variant_sources = {str(row.get("Ref_Key") or "").lower(): row for row, _ in iter_checkpoint_rows(variant_paths)}
    registry.add_count(variant_entity, checkpoint_count(variant_paths))
    source_counts[variant_entity] = checkpoint_count(variant_paths)
    if set(variant_sources) != set(variant_ids):
        missing = sorted(set(variant_ids) - set(variant_sources))
        raise RuntimeError("Live 1C variant closure is incomplete; missing=%d" % len(missing))
    for variant_id in variant_ids:
        source = variant_sources[variant_id]
        owner = str(source.get("Owner") or "").lower()
        owner_type = str(source.get("Owner_Type") or "")
        if owner != variant_product[variant_id] or owner_type != "StandardODATA.Catalog_Номенклатура":
            raise RuntimeError("Variant owner/type mismatch for masked GUID %s…%s" % (variant_id[:6], variant_id[-4:]))
        row = BASE.map_direct(headers["RAW_VARIANTS"], dictionary, "RAW_VARIANTS", source)
        row["variant_id"] = variant_id
        row["product_id"] = owner
        add_provenance(row, variant_entity, variant_id, registry)
        data["RAW_VARIANTS"].append(row)

    print("E1 extraction: classifications", flush=True)
    group_ids = sorted({str(row.get("parent_group_source_id_raw") or "").lower() for row in data["RAW_PRODUCTS"] if row.get("parent_group_source_id_raw") and str(row.get("parent_group_source_id_raw")).lower() != ZERO_GUID})
    group_fields = ["Ref_Key", "Parent_Key", "Description", "Code", "IsFolder", "DeletionMark"]
    registry.register(product_entity, group_fields, "transitive 1C group closure for 204 products")
    group_sources = exact_closure(client, "classifications_1c", product_entity, group_ids, group_fields, parent_field="Parent_Key")
    registry.add_count(product_entity, len(group_sources))
    source_counts[product_entity + "#groups"] = len(group_sources)
    for source in group_sources:
        source_id = str(source["Ref_Key"]).lower()
        row = BASE.make_row(headers["RAW_CLASSIFICATIONS"])
        row.update({
            "classification_id": "1C_GROUP:" + source_id,
            "classification_system": "1C_GROUP",
            "source_category_id": source_id,
            "parent_source_category_id": None if str(source.get("Parent_Key") or "").lower() in {"", ZERO_GUID} else str(source.get("Parent_Key")).lower(),
            "name_raw": source.get("Description"),
            "code_raw": source.get("Code"),
            "is_folder_raw": source.get("IsFolder"),
            "deletion_mark": source.get("DeletionMark"),
        })
        add_provenance(row, product_entity, source_id, registry)
        data["RAW_CLASSIFICATIONS"].append(row)
    for product in data["RAW_PRODUCTS"]:
        parent = str(product.get("parent_group_source_id_raw") or "").lower()
        if not parent or parent == ZERO_GUID:
            continue
        relation_id = product["product_id"] + "|1C_GROUP|" + parent
        row = BASE.make_row(headers["RAW_PRODUCT_CLASSIFICATIONS"])
        row.update({
            "product_classification_id": relation_id,
            "product_id": product["product_id"],
            "source_category_id_raw": parent,
            "classification_id": "1C_GROUP:" + parent,
            "classification_system": "1C_GROUP",
        })
        add_provenance(row, product_entity, relation_id, registry)
        data["RAW_PRODUCT_CLASSIFICATIONS"].append(row)

    web_link_entity = "InformationRegister_iq_КатегорииТоваров"
    web_link_fields = ["Номенклатура_Key", "Категория_Key"]
    registry.register(web_link_entity, web_link_fields, "204 approved yarn product GUIDs")
    web_link_paths = query_scoped_batches(client, "classifications_web_links", web_link_entity, product_ids, "Номенклатура_Key", web_link_fields, batch_size=8, workers=4)
    registry.add_count(web_link_entity, checkpoint_count(web_link_paths))
    source_counts[web_link_entity] = checkpoint_count(web_link_paths)
    web_category_ids = set()
    web_link_seen = set()
    for source, _ in iter_checkpoint_rows(web_link_paths):
        product_id = str(source.get("Номенклатура_Key") or "").lower()
        category_id = str(source.get("Категория_Key") or "").lower()
        if product_id not in set(product_ids) or not GUID_RE.fullmatch(category_id) or category_id == ZERO_GUID:
            continue
        relation_id = product_id + "|WEB_CATEGORY|" + category_id
        if relation_id in web_link_seen:
            continue
        web_link_seen.add(relation_id)
        web_category_ids.add(category_id)
        row = BASE.make_row(headers["RAW_PRODUCT_CLASSIFICATIONS"])
        row.update({
            "product_classification_id": relation_id,
            "product_id": product_id,
            "source_category_id_raw": category_id,
            "classification_id": "WEB_CATEGORY:" + category_id,
            "classification_system": "WEB_CATEGORY",
        })
        add_provenance(row, web_link_entity, relation_id, registry)
        data["RAW_PRODUCT_CLASSIFICATIONS"].append(row)
    source_exclusions["products_without_web_category"] = sorted(set(product_ids) - {row["product_id"] for row in data["RAW_PRODUCT_CLASSIFICATIONS"] if row["classification_system"] == "WEB_CATEGORY"})

    web_category_entity = "Catalog_iq_Категории"
    web_category_fields = ["Ref_Key", "Parent_Key", "Description", "Code", "Описание", "meta_title", "meta_description", "meta_keyword", "DeletionMark"]
    registry.register(web_category_entity, web_category_fields, "transitive referenced web-category closure")
    web_category_sources = exact_closure(client, "classifications_web", web_category_entity, sorted(web_category_ids), web_category_fields, parent_field="Parent_Key")
    registry.add_count(web_category_entity, len(web_category_sources))
    source_counts[web_category_entity] = len(web_category_sources)
    source_exclusions["Catalog_iq_Категории.IsFolder"] = {
        "status": "SOURCE_PROPERTY_UNAVAILABLE",
        "evidence": "OData HTTP 400 code 6: path segment IsFolder not found",
        "contract_field": "RAW_CLASSIFICATIONS.is_folder_raw",
        "handling": "nullable field retained as NULL; no value fabricated",
    }
    for source in web_category_sources:
        source_id = str(source["Ref_Key"]).lower()
        row = BASE.make_row(headers["RAW_CLASSIFICATIONS"])
        row.update({
            "classification_id": "WEB_CATEGORY:" + source_id,
            "classification_system": "WEB_CATEGORY",
            "source_category_id": source_id,
            "parent_source_category_id": None if str(source.get("Parent_Key") or "").lower() in {"", ZERO_GUID} else str(source.get("Parent_Key")).lower(),
            "name_raw": source.get("Description"),
            "code_raw": source.get("Code"),
            "description_raw": source.get("Описание"),
            "meta_title_raw": source.get("meta_title"),
            "meta_description_raw": source.get("meta_description"),
            "meta_keywords_raw": source.get("meta_keyword"),
            "is_folder_raw": source.get("IsFolder"),
            "deletion_mark": source.get("DeletionMark"),
        })
        add_provenance(row, web_category_entity, source_id, registry)
        data["RAW_CLASSIFICATIONS"].append(row)

    print("E1 extraction: lookups", flush=True)
    manufacturer_entity = "Catalog_Производители"
    manufacturer_fields = BASE.direct_source_properties(dictionary, "RAW_MANUFACTURERS", manufacturer_entity)
    manufacturer_ids = sorted({str(row.get("manufacturer_id") or "").lower() for row in data["RAW_PRODUCTS"] if row.get("manufacturer_id") and str(row.get("manufacturer_id")).lower() != ZERO_GUID})
    registry.register(manufacturer_entity, manufacturer_fields, "referenced manufacturer closure")
    manufacturer_sources = exact_closure(client, "manufacturers", manufacturer_entity, manufacturer_ids, manufacturer_fields, parent_field="Parent_Key")
    registry.add_count(manufacturer_entity, len(manufacturer_sources))
    source_counts[manufacturer_entity] = len(manufacturer_sources)
    for source in manufacturer_sources:
        record_id = str(source["Ref_Key"]).lower()
        row = BASE.map_direct(headers["RAW_MANUFACTURERS"], dictionary, "RAW_MANUFACTURERS", source)
        row["manufacturer_id"] = record_id
        add_provenance(row, manufacturer_entity, record_id, registry)
        data["RAW_MANUFACTURERS"].append(row)

    package_entity = "Catalog_НаборыУпаковок"
    package_fields = BASE.direct_source_properties(dictionary, "RAW_PACKAGE_SETS", package_entity)
    package_ids = sorted({str(row.get("package_set_id") or "").lower() for row in data["RAW_PRODUCTS"] if row.get("package_set_id") and str(row.get("package_set_id")).lower() != ZERO_GUID})
    registry.register(package_entity, package_fields, "referenced package-set closure")
    package_sources = exact_closure(client, "package_sets", package_entity, package_ids, package_fields)
    registry.add_count(package_entity, len(package_sources))
    source_counts[package_entity] = len(package_sources)
    for source in package_sources:
        record_id = str(source["Ref_Key"]).lower()
        row = BASE.map_direct(headers["RAW_PACKAGE_SETS"], dictionary, "RAW_PACKAGE_SETS", source)
        row["package_set_id"] = record_id
        add_provenance(row, package_entity, record_id, registry)
        data["RAW_PACKAGE_SETS"].append(row)

    unit_entity = "Catalog_УпаковкиЕдиницыИзмерения"
    unit_fields = BASE.direct_source_properties(dictionary, "RAW_UNIT_DEFINITIONS", unit_entity)
    unit_ids = {
        str(value).lower()
        for product in data["RAW_PRODUCTS"]
        for value in [product.get("base_unit_id"), product.get("report_unit_id"), product.get("weight_unit_id"), product.get("length_unit_id")]
        if value and str(value).lower() != ZERO_GUID
    }
    for package in data["RAW_PACKAGE_SETS"]:
        for field in ["base_unit_id", "report_unit_id"]:
            value = package.get(field)
            if value and str(value).lower() != ZERO_GUID:
                unit_ids.add(str(value).lower())
    registry.register(unit_entity, unit_fields, "referenced unit closure")
    unit_sources = exact_closure(client, "unit_definitions", unit_entity, sorted(unit_ids), unit_fields, parent_field="ЕдиницаИзмерения_Key")
    registry.add_count(unit_entity, len(unit_sources))
    source_counts[unit_entity] = len(unit_sources)
    for source in unit_sources:
        record_id = str(source["Ref_Key"]).lower()
        row = BASE.map_direct(headers["RAW_UNIT_DEFINITIONS"], dictionary, "RAW_UNIT_DEFINITIONS", source)
        row["unit_id"] = record_id
        add_provenance(row, unit_entity, record_id, registry)
        data["RAW_UNIT_DEFINITIONS"].append(row)

    warehouse_map = {key.lower(): value for key, value in read_json(WAREHOUSE_MAP_JSON).items()}
    warehouse_ids = sorted(warehouse_map)
    warehouse_entity = "Catalog_Склады"
    warehouse_fields = BASE.direct_source_properties(dictionary, "RAW_WAREHOUSES", warehouse_entity)
    registry.register(warehouse_entity, warehouse_fields, "8 approved virtual warehouses")
    warehouse_sources = exact_closure(client, "warehouses", warehouse_entity, warehouse_ids, warehouse_fields)
    registry.add_count(warehouse_entity, len(warehouse_sources))
    source_counts[warehouse_entity] = len(warehouse_sources)
    if len(warehouse_sources) != 8:
        raise RuntimeError("Approved warehouse closure is not exactly 8")
    for source in warehouse_sources:
        record_id = str(source["Ref_Key"]).lower()
        row = BASE.map_direct(headers["RAW_WAREHOUSES"], dictionary, "RAW_WAREHOUSES", source)
        row["warehouse_id"] = record_id
        add_provenance(row, warehouse_entity, record_id, registry)
        data["RAW_WAREHOUSES"].append(row)

    all_price_types = {key.lower(): value for key, value in read_json(PRICE_TYPE_MAP_JSON).items()}
    price_type_ids = sorted(key for key, name in all_price_types.items() if name in APPROVED_PRICE_TYPE_NAMES)
    if len(price_type_ids) != 10:
        raise RuntimeError("Approved price-type scope is not exactly 10")
    source_exclusions["price_types_outside_approved_phase1_scope"] = {
        key: name for key, name in all_price_types.items() if key not in set(price_type_ids)
    }
    price_type_entity = "Catalog_ВидыЦен"
    price_type_fields = BASE.direct_source_properties(dictionary, "RAW_PRICE_TYPES", price_type_entity)
    registry.register(price_type_entity, price_type_fields, "10 approved price types")
    price_type_sources = exact_closure(client, "price_types", price_type_entity, price_type_ids, price_type_fields)
    registry.add_count(price_type_entity, len(price_type_sources))
    source_counts[price_type_entity] = len(price_type_sources)
    for source in price_type_sources:
        record_id = str(source["Ref_Key"]).lower()
        row = BASE.map_direct(headers["RAW_PRICE_TYPES"], dictionary, "RAW_PRICE_TYPES", source)
        row["price_type_id"] = record_id
        add_provenance(row, price_type_entity, record_id, registry)
        data["RAW_PRICE_TYPES"].append(row)

    print("E1 extraction: variant image links and color closure", flush=True)
    link_entity = "Catalog_iq_ИзображенияХарактеристик"
    link_fields = BASE.direct_source_properties(dictionary, "RAW_VARIANT_IMAGE_LINKS", link_entity)
    registry.register(link_entity, link_fields, "204 approved yarn product GUIDs")
    link_paths = query_scoped_batches(client, "variant_image_links", link_entity, product_ids, "Номенклатура_Key", link_fields, batch_size=8, workers=4)
    registry.add_count(link_entity, checkpoint_count(link_paths))
    source_counts[link_entity] = checkpoint_count(link_paths)
    excluded_links = []
    for source, _ in iter_checkpoint_rows(link_paths):
        product_id = str(source.get("Номенклатура_Key") or "").lower()
        variant_id = str(source.get("Характеристика_Key") or "").lower()
        if product_id not in set(product_ids) or variant_id not in set(variant_ids) or variant_product[variant_id] != product_id:
            excluded_links.append({"product_id": product_id, "variant_id": variant_id, "reason": "outside approved exact variant scope"})
            continue
        record_id = str(source.get("Ref_Key") or "").lower()
        row = BASE.map_direct(headers["RAW_VARIANT_IMAGE_LINKS"], dictionary, "RAW_VARIANT_IMAGE_LINKS", source)
        row["variant_image_link_id"] = record_id
        add_provenance(row, link_entity, record_id, registry)
        data["RAW_VARIANT_IMAGE_LINKS"].append(row)
    source_exclusions["variant_image_links"] = excluded_links
    if len(data["RAW_VARIANT_IMAGE_LINKS"]) != 6173:
        raise RuntimeError("Live variant image-link count differs from approved 6,173")

    color_scheme_entity = "Catalog_iq_ЦветоваяСхема"
    color_scheme_fields = BASE.direct_source_properties(dictionary, "RAW_COLOR_SCHEMES", color_scheme_entity)
    color_scheme_ids = sorted({str(row.get("color_scheme_id") or "").lower() for row in data["RAW_VARIANT_IMAGE_LINKS"] if row.get("color_scheme_id") and str(row.get("color_scheme_id")).lower() != ZERO_GUID})
    registry.register(color_scheme_entity, color_scheme_fields, "referenced color-scheme closure")
    color_scheme_sources = exact_closure(client, "color_schemes", color_scheme_entity, color_scheme_ids, color_scheme_fields)
    registry.add_count(color_scheme_entity, len(color_scheme_sources))
    source_counts[color_scheme_entity] = len(color_scheme_sources)
    for source in color_scheme_sources:
        record_id = str(source["Ref_Key"]).lower()
        row = BASE.map_direct(headers["RAW_COLOR_SCHEMES"], dictionary, "RAW_COLOR_SCHEMES", source)
        row["color_scheme_id"] = record_id
        add_provenance(row, color_scheme_entity, record_id, registry)
        data["RAW_COLOR_SCHEMES"].append(row)

    palette_entity = "Catalog_iq_ЦветоваяПалитра"
    palette_fields = BASE.direct_source_properties(dictionary, "RAW_COLOR_PALETTES", palette_entity)
    palette_ids = sorted({str(row.get("palette_id") or "").lower() for row in data["RAW_COLOR_SCHEMES"] if row.get("palette_id") and str(row.get("palette_id")).lower() != ZERO_GUID})
    registry.register(palette_entity, palette_fields, "referenced color-palette closure")
    palette_sources = exact_closure(client, "color_palettes", palette_entity, palette_ids, palette_fields)
    registry.add_count(palette_entity, len(palette_sources))
    source_counts[palette_entity] = len(palette_sources)
    for source in palette_sources:
        record_id = str(source["Ref_Key"]).lower()
        row = BASE.map_direct(headers["RAW_COLOR_PALETTES"], dictionary, "RAW_COLOR_PALETTES", source)
        row["palette_id"] = record_id
        add_provenance(row, palette_entity, record_id, registry)
        data["RAW_COLOR_PALETTES"].append(row)

    print("E1 extraction: attached files", flush=True)
    variant_file_ids = sorted({str(row.get("variant_file_id") or "").lower() for row in data["RAW_VARIANT_IMAGE_LINKS"] if row.get("variant_file_id") and str(row.get("variant_file_id")).lower() != ZERO_GUID})
    variant_file_entity = "Catalog_iq_ИзображенияХарактеристикПрисоединенныеФайлы"
    variant_file_fields = BASE.direct_source_properties(dictionary, "RAW_VARIANT_FILES", variant_file_entity)
    registry.register(variant_file_entity, variant_file_fields, "unique nonzero file GUIDs referenced by 6,173 image links")
    variant_file_paths = query_scoped_batches(client, "variant_files", variant_file_entity, variant_file_ids, "Ref_Key", variant_file_fields, batch_size=12, workers=6)
    registry.add_count(variant_file_entity, checkpoint_count(variant_file_paths))
    source_counts[variant_file_entity] = checkpoint_count(variant_file_paths)
    variant_file_sources = {str(row.get("Ref_Key") or "").lower(): row for row, _ in iter_checkpoint_rows(variant_file_paths)}
    if set(variant_file_sources) != set(variant_file_ids):
        missing = sorted(set(variant_file_ids) - set(variant_file_sources))
        raise RuntimeError("Variant attached-file closure is incomplete; missing=%d" % len(missing))
    for record_id in sorted(variant_file_sources):
        source = variant_file_sources[record_id]
        row = BASE.map_direct(headers["RAW_VARIANT_FILES"], dictionary, "RAW_VARIANT_FILES", source)
        row["file_id"] = record_id
        row["owner_type"] = "StandardODATA.Catalog_iq_ИзображенияХарактеристик"
        row["binary_storage_id"] = BASE.binary_key(record_id, VARIANT_FILE_TYPE)
        add_provenance(row, variant_file_entity, record_id, registry)
        data["RAW_VARIANT_FILES"].append(row)

    product_file_entity = "Catalog_НоменклатураПрисоединенныеФайлы"
    product_file_fields = BASE.direct_source_properties(dictionary, "RAW_PRODUCT_FILES", product_file_entity)
    registry.register(product_file_entity, product_file_fields, "all attached files owned by 204 approved products")
    product_file_paths = query_scoped_batches(client, "product_files", product_file_entity, product_ids, "ВладелецФайла_Key", product_file_fields, batch_size=8, workers=4)
    registry.add_count(product_file_entity, checkpoint_count(product_file_paths))
    source_counts[product_file_entity] = checkpoint_count(product_file_paths)
    main_images = {row["product_id"]: str(row.get("main_image_file_id") or "").lower() for row in data["RAW_PRODUCTS"]}
    product_file_seen = set()
    for source, _ in iter_checkpoint_rows(product_file_paths):
        record_id = str(source.get("Ref_Key") or "").lower()
        owner_id = str(source.get("ВладелецФайла_Key") or "").lower()
        if record_id in product_file_seen:
            continue
        product_file_seen.add(record_id)
        if owner_id not in set(product_ids):
            raise RuntimeError("Product file owner is outside the approved scope")
        row = BASE.map_direct(headers["RAW_PRODUCT_FILES"], dictionary, "RAW_PRODUCT_FILES", source)
        row["file_id"] = record_id
        row["owner_type"] = "StandardODATA.Catalog_Номенклатура"
        row["is_primary_derived"] = record_id == main_images.get(owner_id)
        row["binary_storage_id"] = BASE.binary_key(record_id, PRODUCT_FILE_TYPE)
        add_provenance(row, product_file_entity, record_id, registry)
        data["RAW_PRODUCT_FILES"].append(row)

    print("E1 extraction: website descriptions and attributes", flush=True)
    website_description_entity = "Catalog_iq_ОписаниеТовара"
    website_description_fields = ["Ref_Key", "Owner_Key", "Текст", "ТекстHTML", "DeletionMark"]
    registry.register(website_description_entity, website_description_fields, "204 approved yarn product GUIDs")
    website_description_paths = query_scoped_batches(client, "website_descriptions", website_description_entity, product_ids, "Owner_Key", website_description_fields, batch_size=8, workers=4)
    registry.add_count(website_description_entity, checkpoint_count(website_description_paths))
    source_counts[website_description_entity] = checkpoint_count(website_description_paths)
    for source, _ in iter_checkpoint_rows(website_description_paths):
        owner_id = str(source.get("Owner_Key") or "").lower()
        record_id = str(source.get("Ref_Key") or source_record_hash(source)).lower()
        if owner_id not in set(product_ids):
            continue
        if source.get("Текст") not in (None, ""):
            data["RAW_DESCRIPTIONS"].append(description_row(headers, owner_id, "WEBSITE_PLAIN", "TEXT", source.get("Текст"), source.get("DeletionMark"), website_description_entity, record_id + "|TEXT", registry))
        if source.get("ТекстHTML") not in (None, ""):
            data["RAW_DESCRIPTIONS"].append(description_row(headers, owner_id, "WEBSITE_HTML", "HTML", source.get("ТекстHTML"), source.get("DeletionMark"), website_description_entity, record_id + "|HTML", registry))

    attribute_value_entity = "InformationRegister_iq_ФильтрыТоваровИнтернетМагазина"
    attribute_value_fields = ["Номенклатура_Key", "Фильтр_Key", "Значение"]
    registry.register(attribute_value_entity, attribute_value_fields, "204 approved yarn product GUIDs")
    attribute_value_paths = query_scoped_batches(client, "attribute_values", attribute_value_entity, product_ids, "Номенклатура_Key", attribute_value_fields, batch_size=8, workers=4)
    registry.add_count(attribute_value_entity, checkpoint_count(attribute_value_paths))
    source_counts[attribute_value_entity] = checkpoint_count(attribute_value_paths)
    attribute_ids = set()
    for source, _ in iter_checkpoint_rows(attribute_value_paths):
        owner_id = str(source.get("Номенклатура_Key") or "").lower()
        attribute_id = str(source.get("Фильтр_Key") or "").lower()
        if owner_id not in set(product_ids) or not GUID_RE.fullmatch(attribute_id) or attribute_id == ZERO_GUID:
            continue
        source_id = source_record_hash(source)
        row = BASE.make_row(headers["RAW_ATTRIBUTE_VALUES"])
        row.update({
            "attribute_value_id": owner_id + "|" + attribute_id + "|" + source_id,
            "owner_type": "PRODUCT",
            "owner_id": owner_id,
            "attribute_definition_id": attribute_id,
            "value_raw": source.get("Значение"),
        })
        add_provenance(row, attribute_value_entity, source_id, registry)
        data["RAW_ATTRIBUTE_VALUES"].append(row)
        attribute_ids.add(attribute_id)

    attribute_definition_entity = "Catalog_iq_Фильтры"
    attribute_definition_fields = BASE.direct_source_properties(dictionary, "RAW_ATTRIBUTE_DEFINITIONS", attribute_definition_entity)
    registry.register(attribute_definition_entity, attribute_definition_fields, "referenced filter definitions and parents")
    attribute_definition_sources = exact_closure(client, "attribute_definitions", attribute_definition_entity, sorted(attribute_ids), attribute_definition_fields, parent_field="Parent_Key")
    registry.add_count(attribute_definition_entity, len(attribute_definition_sources))
    source_counts[attribute_definition_entity] = len(attribute_definition_sources)
    for source in attribute_definition_sources:
        record_id = str(source["Ref_Key"]).lower()
        row = BASE.map_direct(headers["RAW_ATTRIBUTE_DEFINITIONS"], dictionary, "RAW_ATTRIBUTE_DEFINITIONS", source)
        row["attribute_definition_id"] = record_id
        add_provenance(row, attribute_definition_entity, record_id, registry)
        data["RAW_ATTRIBUTE_DEFINITIONS"].append(row)

    print("E1 extraction: current prices", flush=True)
    price_entity = "InformationRegister_ЦеныНоменклатуры_RecordType"
    price_fields = ["Recorder", "Recorder_Type", "LineNumber", "Period", "Active", "Номенклатура_Key", "Характеристика_Key", "ВидЦены_Key", "Цена", "Упаковка_Key", "Валюта_Key"]
    registry.register(price_entity, price_fields, "204 products; Active=true; one cutoff; 10 approved price types")
    price_paths = query_scoped_batches(client, "current_price_inputs", price_entity, product_ids, "Номенклатура_Key", price_fields, batch_size=8, extra_filter="Active eq true", workers=4)
    registry.add_count(price_entity, checkpoint_count(price_paths))
    source_counts[price_entity] = checkpoint_count(price_paths)
    price_exclusions = defaultdict(int)
    selected_price_sources = []
    approved_price_ids = set(price_type_ids)
    approved_product_ids = set(product_ids)
    approved_variant_ids = set(variant_ids)
    for path in price_paths:
        payload = read_json(path)
        candidates: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
        for source in payload.get("rows", []):
            product_id = str(source.get("Номенклатура_Key") or "").lower()
            variant_id = str(source.get("Характеристика_Key") or "").lower()
            price_type_id = str(source.get("ВидЦены_Key") or "").lower()
            period = BASE.normalize_datetime(source.get("Period"))
            if product_id not in approved_product_ids:
                price_exclusions["product_outside_scope"] += 1
            elif variant_id not in approved_variant_ids and variant_id != ZERO_GUID:
                price_exclusions["variant_outside_scope"] += 1
            elif price_type_id not in approved_price_ids:
                price_exclusions["price_type_outside_approved_phase1_scope"] += 1
            elif not period or period > cutoff:
                price_exclusions["period_after_cutoff_or_invalid"] += 1
            else:
                candidates[(product_id, variant_id, price_type_id)].append(source)
        for key, values in candidates.items():
            latest_period = max(BASE.normalize_datetime(value.get("Period")) or "" for value in values)
            winners = [value for value in values if BASE.normalize_datetime(value.get("Period")) == latest_period]
            if len(winners) != 1:
                raise RuntimeError("Current-price latest-period tie for one approved key")
            source = winners[0]
            selected_price_sources.append(source)
            product_id, variant_id, price_type_id = key
            row = BASE.make_row(headers["RAW_CURRENT_PRICES"])
            row.update({
                "current_price_id": product_id + "|" + variant_id + "|" + price_type_id,
                "product_id": product_id,
                "variant_id_raw": variant_id,
                "variant_id": None if variant_id == ZERO_GUID else variant_id,
                "price_type_id": price_type_id,
                "price_value": source.get("Цена"),
                "currency_id_raw": None if str(source.get("Валюта_Key") or "").lower() in {"", ZERO_GUID} else str(source.get("Валюта_Key")).lower(),
                "package_id_raw": None if str(source.get("Упаковка_Key") or "").lower() in {"", ZERO_GUID} else str(source.get("Упаковка_Key")).lower(),
                "effective_period": BASE.normalize_datetime(source.get("Period")),
                "cutoff_at_utc": cutoff,
                "selection_rule": "MAX(Period) WHERE Active=true AND Period<=cutoff; reject ties; approved Phase 1 price types",
                "recorder_id_raw": source.get("Recorder"),
            })
            add_provenance(row, price_entity, BASE.source_record_id_price(source), registry)
            data["RAW_CURRENT_PRICES"].append(row)
    atomic_json(RAW_DIR / "source_evidence" / "current_price_selected_source.json", sorted_source_rows(selected_price_sources))
    source_exclusions["current_prices"] = dict(price_exclusions)

    print("E1 extraction: current stock", flush=True)
    stock_entity = "AccumulationRegister_СвободныеОстатки_RecordType"
    stock_fields = ["Recorder", "Recorder_Type", "Period", "LineNumber", "Active", "RecordType", "Номенклатура_Key", "Характеристика_Key", "Склад_Key", "ВНаличии"]
    registry.register(stock_entity, stock_fields, "204 products; Active=true; one cutoff; 8 approved warehouses")
    stock_paths = query_scoped_batches(client, "current_stock_inputs", stock_entity, product_ids, "Номенклатура_Key", stock_fields, batch_size=8, extra_filter="Active eq true", workers=4)
    registry.add_count(stock_entity, checkpoint_count(stock_paths))
    source_counts[stock_entity] = checkpoint_count(stock_paths)
    stock_exclusions = defaultdict(int)
    stock_source_total = 0.0
    approved_warehouse_ids = set(warehouse_ids)
    for path in stock_paths:
        payload = read_json(path)
        batch_product_ids = [value.lower() for value in payload.get("scope_ids", [])]
        grouped: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
        for source in payload.get("rows", []):
            product_id = str(source.get("Номенклатура_Key") or "").lower()
            variant_id = str(source.get("Характеристика_Key") or "").lower()
            warehouse_id = str(source.get("Склад_Key") or "").lower()
            period = BASE.normalize_datetime(source.get("Period"))
            if product_id not in approved_product_ids:
                stock_exclusions["product_outside_scope"] += 1
            elif variant_id not in approved_variant_ids or variant_product.get(variant_id) != product_id:
                stock_exclusions["variant_outside_scope"] += 1
            elif warehouse_id not in approved_warehouse_ids:
                stock_exclusions["warehouse_outside_approved_phase1_scope"] += 1
            elif not period or period > cutoff:
                stock_exclusions["period_after_cutoff_or_invalid"] += 1
            else:
                grouped[(product_id, variant_id, warehouse_id)].append(source)
        for product_id in batch_product_ids:
            for variant_id in variants_by_product[product_id]:
                for warehouse_id in warehouse_ids:
                    contributing = sorted_source_rows(grouped.get((product_id, variant_id, warehouse_id), []))
                    quantity = 0.0
                    for source in contributing:
                        sign = 1.0 if source.get("RecordType") == "Receipt" else -1.0
                        quantity += sign * float(source.get("ВНаличии") or 0)
                    quantity = round(quantity, 6)
                    stock_source_total += quantity
                    row = BASE.make_row(headers["RAW_CURRENT_STOCK"])
                    row.update({
                        "current_stock_id": product_id + "|" + variant_id + "|" + warehouse_id,
                        "product_id": product_id,
                        "variant_id": variant_id,
                        "warehouse_id": warehouse_id,
                        "quantity_available": quantity,
                        "cutoff_at_utc": cutoff,
                        "aggregation_rule": "SUM(Receipt:+1, other RecordType:-1)*ВНаличии; Active=true; Period<=cutoff; v1",
                        "source_record_count": len(contributing),
                        "is_explicit_zero": abs(quantity) < 1e-9,
                        "source_system_id": SOURCE_SYSTEM_ID,
                        "source_entityset": stock_entity,
                        "input_checksum_sha256": sha256_bytes(canonical_json(contributing)),
                        "extraction_run_id": registry.run_id(stock_entity),
                    })
                    data["RAW_CURRENT_STOCK"].append(row)
    normalized_stock_total = round(sum(float(row["quantity_available"]) for row in data["RAW_CURRENT_STOCK"]), 6)
    stock_reconciliation_pass = abs(round(stock_source_total, 6) - normalized_stock_total) < 1e-6
    source_exclusions["current_stock"] = dict(stock_exclusions)
    if len(data["RAW_CURRENT_STOCK"]) != 9114 * 8 or not stock_reconciliation_pass:
        raise RuntimeError("Current stock matrix/reconciliation failed")

    print("E1 extraction: binary storage metadata", flush=True)
    binary_entity = "InformationRegister_ДвоичныеДанныеФайлов"
    binary_fields = ["Файл", "Файл_Type", "ДвоичныеДанныеФайла_Type", "ДвоичныеДанныеФайла_Base64Data"]
    registry.register(binary_entity, binary_fields, "direct composite keys for all E1 product/variant files")
    binary_requests = sorted(
        [(row["file_id"], VARIANT_FILE_TYPE) for row in data["RAW_VARIANT_FILES"]]
        + [(row["file_id"], PRODUCT_FILE_TYPE) for row in data["RAW_PRODUCT_FILES"]]
    )
    data["RAW_BINARY_STORAGE_METADATA"] = extract_binary_metadata(client, binary_requests, headers, registry, cutoff)
    registry.add_count(binary_entity, len(data["RAW_BINARY_STORAGE_METADATA"]))
    source_counts[binary_entity] = len(data["RAW_BINARY_STORAGE_METADATA"])

    source_rows = [
        {
            "source_system_id": SOURCE_SYSTEM_ID,
            "source_system_name": "1C Standard OData",
            "source_system_type": "ODATA",
            "access_mode": "READ_ONLY",
            "endpoint_reference": "ODATA_BASE_URL from local secrets",
            "credentials_reference": "ODATA_USERNAME/ODATA_PASSWORD from local secrets",
            "active": True,
            "notes": "No credentials or protected URL persisted",
        },
        {
            "source_system_id": "CONTRACT",
            "source_system_name": "RAW COMPLETE v1 approved contract",
            "source_system_type": "CONTRACT",
            "access_mode": "READ_ONLY",
            "active": True,
            "notes": "Frozen 32-sheet/466-field contract",
        },
        {
            "source_system_id": "AI_FACTORY_DERIVATION",
            "source_system_name": "AI Factory deterministic derivation",
            "source_system_type": "DERIVATION",
            "access_mode": "LOCAL_ONLY",
            "active": True,
            "notes": "Current stock aggregation and technical controls only",
        },
    ]
    data["RAW_SOURCE_SYSTEMS"] = [{field: source.get(field) for field in headers["RAW_SOURCE_SYSTEMS"]} for source in source_rows]

    dictionary_path = CONTRACT / "RAW_COMPLETE_V1_DATA_DICTIONARY.csv"
    mapping_path = CONTRACT / "RAW_COMPLETE_V1_ENTITYSET_MAPPING.csv"
    schema_row = BASE.make_row(headers["RAW_SCHEMA_VERSIONS"])
    schema_row.update({
        "schema_version_id": SCHEMA_VERSION_ID,
        "version_label": "RAW COMPLETE v1",
        "contract_status": "APPROVED",
        "created_at_utc": started,
        "approved_at_utc": started,
        "approved_by": "PROJECT_OWNER",
        "dictionary_checksum_sha256": sha256_bytes(dictionary_path.read_bytes()),
        "mapping_checksum_sha256": sha256_bytes(mapping_path.read_bytes()),
        "notes": "E1 Phase 1 full snapshot",
    })
    data["RAW_SCHEMA_VERSIONS"].append(schema_row)
    data["RAW_DATA_DICTIONARY"] = [{field: item.get(field) for field in headers["RAW_DATA_DICTIONARY"]} for item in dictionary]
    data["RAW_ENTITYSET_MAPPING"] = [{field: item.get(field) for field in headers["RAW_ENTITYSET_MAPPING"]} for item in mappings]

    data["RAW_EXTRACTION_RUNS"] = registry.finalize(data)
    required_null_profile = []
    for item in dictionary:
        if item["nullable"] != "NO" or item["source_system"] != SOURCE_SYSTEM_ID:
            continue
        sheet = item["sheet_name"]
        field = item["field_name"]
        missing = [index + 2 for index, row in enumerate(data[sheet]) if row.get(field) in (None, "")]
        required_null_profile.append({
            "sheet": sheet,
            "field": field,
            "rows_in_scope": len(data[sheet]),
            "missing_rows": missing,
            "status": "PASS" if not missing else "FAIL",
        })

    write_normalized(data, order, headers, dictionary)
    row_counts = {sheet: len(data[sheet]) for sheet in order}
    manifest = {
        "snapshot_id": context["run_id"],
        "schema_version_id": SCHEMA_VERSION_ID,
        "created_at_utc": started,
        "cutoff_at_utc": cutoff,
        "source_system_id": SOURCE_SYSTEM_ID,
        "scope": {"products": 204, "variants": 9114},
        "sheet_order": order,
        "field_count": sum(len(headers[sheet]) for sheet in order),
        "row_counts": row_counts,
        "binary_payload_persisted": False,
        "extractor_version": EXTRACTOR_VERSION,
    }
    extraction_summary = {
        "status": "EXTRACTED_PENDING_VALIDATION",
        "snapshot_id": context["run_id"],
        "cutoff_at_utc": cutoff,
        "products": len(data["RAW_PRODUCTS"]),
        "variants": len(data["RAW_VARIANTS"]),
        "variant_image_links": len(data["RAW_VARIANT_IMAGE_LINKS"]),
        "variant_files": len(data["RAW_VARIANT_FILES"]),
        "product_files": len(data["RAW_PRODUCT_FILES"]),
        "binary_metadata": len(data["RAW_BINARY_STORAGE_METADATA"]),
        "current_prices": len(data["RAW_CURRENT_PRICES"]),
        "current_stock": len(data["RAW_CURRENT_STOCK"]),
        "stock_source_total": round(stock_source_total, 6),
        "stock_normalized_total": normalized_stock_total,
        "stock_reconciliation_pass": stock_reconciliation_pass,
        "source_counts": source_counts,
        "source_exclusions": source_exclusions,
        "raw_payload_policy": "Source JSON retained in bounded checkpoints; binary/Base64 never persisted",
    }
    atomic_json(SNAPSHOT / "manifest.json", manifest)
    atomic_json(SNAPSHOT / "row_counts.json", row_counts)
    atomic_json(SNAPSHOT / "required_null_profile.json", required_null_profile)
    atomic_json(SNAPSHOT / "extraction_summary.json", extraction_summary)
    atomic_json(SNAPSHOT / "source_exclusions.json", source_exclusions)
    print("E1 extraction complete: products=%d variants=%d" % (row_counts["RAW_PRODUCTS"], row_counts["RAW_VARIANTS"]), flush=True)
    return extraction_summary


def load_snapshot_data() -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
    dictionary = BASE.read_csv(CONTRACT / "RAW_COMPLETE_V1_DATA_DICTIONARY.csv")
    mappings = BASE.read_csv(CONTRACT / "RAW_COMPLETE_V1_ENTITYSET_MAPPING.csv")
    matrix = BASE.read_csv(CONTRACT / "RAW_COMPLETE_V1_VALIDATION_MATRIX.csv")
    order, headers = BASE.get_headers(dictionary)
    manifest = read_json(SNAPSHOT / "manifest.json")
    null_profile = read_json(SNAPSHOT / "required_null_profile.json")
    summary = read_json(SNAPSHOT / "extraction_summary.json")
    types = {(item["sheet_name"], item["field_name"]): item["data_type"] for item in dictionary}
    data: Dict[str, List[Dict[str, Any]]] = {}
    for sheet in order:
        with (NORMALIZED_DIR / (sheet + ".csv")).open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
        if not rows or rows[0] != headers[sheet]:
            raise RuntimeError("Normalized E1 header mismatch in " + sheet)
        typed = []
        for values in rows[1:]:
            padded = values + [""] * (len(headers[sheet]) - len(values))
            typed.append({
                field: BASE.fixture_value(padded[index], types[(sheet, field)])
                for index, field in enumerate(headers[sheet])
            })
        data[sheet] = typed
    selected_price_source = read_json(RAW_DIR / "source_evidence" / "current_price_selected_source.json")
    ctx = {
        "dictionary": dictionary,
        "mappings": mappings,
        "matrix": matrix,
        "order": order,
        "headers": headers,
        "manifest": manifest,
        "null_profile": null_profile,
        "raw": {"InformationRegister_ЦеныНоменклатуры_RecordType": selected_price_source},
        "scope_validation": {
            "product_count": 204,
            "variant_count": 9114,
            "image_link_count": 6173,
            "warehouse_count": 8,
            "product_ids": [row["product_id"] for row in data["RAW_PRODUCTS"]],
            "variant_ids": [row["variant_id"] for row in data["RAW_VARIANTS"]],
        },
        "stock_reconciliation_pass": bool(summary.get("stock_reconciliation_pass")),
    }
    return data, ctx


def finalize_snapshot_checksums() -> None:
    files = []
    for path in SNAPSHOT.rglob("*"):
        if not path.is_file() or path.name == "checksums.sha256":
            continue
        relative = path.relative_to(SNAPSHOT)
        if relative.parts and relative.parts[0] == "load":
            continue
        files.append(path)
    lines = [sha256_bytes(path.read_bytes()) + "  " + str(path.relative_to(SNAPSHOT)) for path in sorted(files)]
    (SNAPSHOT / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_snapshot_checksums() -> Dict[str, Any]:
    path = SNAPSHOT / "checksums.sha256"
    failures = []
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        target = SNAPSHOT / relative
        actual = sha256_bytes(target.read_bytes()) if target.is_file() else None
        count += 1
        if actual != expected:
            failures.append({"path": relative, "expected": expected, "actual": actual})
    return {"status": "PASS" if not failures else "FAIL", "checked": count, "failures": failures, "manifest_sha256": sha256_bytes(path.read_bytes())}


def validate_e1_snapshot() -> Dict[str, Any]:
    data, ctx = load_snapshot_data()
    report = BASE.validate_fixture(data, ctx, output_path=SNAPSHOT / "validation_results.json")
    descriptions_ok = all(
        int(row["content_length"]) == len(str(row.get("content_raw") or ""))
        and row["content_sha256"] == sha256_bytes(str(row.get("content_raw") or "").encode("utf-8"))
        and int(row["content_length"]) <= 50000
        for row in data["RAW_DESCRIPTIONS"]
    )
    product_codes = [str(row.get("code_1c") or "") for row in data["RAW_PRODUCTS"]]
    variant_descriptions = [str(row.get("description_raw") or "") for row in data["RAW_VARIANTS"]]
    leading_zero_values = sorted({value for value in product_codes + variant_descriptions if re.search(r"(^|[^0-9])0[0-9]", value)})
    additional = {
        "scope_exact": len(data["RAW_PRODUCTS"]) == 204 and len(data["RAW_VARIANTS"]) == 9114,
        "stock_rows_exact": len(data["RAW_CURRENT_STOCK"]) == 9114 * 8,
        "stock_reconciliation_pass": bool(ctx["stock_reconciliation_pass"]),
        "description_hash_length_pass": descriptions_ok,
        "leading_zero_values_preserved": bool(leading_zero_values),
        "binary_payload_not_in_normalized_fields": all("Base64Data" not in field for fields in ctx["headers"].values() for field in fields),
    }
    status = "PASS" if report["status"] == "PASS" and report["validation_count"] == 171 and report["passed"] == 171 and all(additional.values()) else "FAIL"
    summary = read_json(SNAPSHOT / "extraction_summary.json")
    summary["status"] = "VALIDATED" if status == "PASS" else "VALIDATION_FAILED"
    summary["validation"] = {"status": status, "total": report["validation_count"], "passed": report["passed"], "failed": report["failed"], "additional": additional}
    atomic_json(SNAPSHOT / "extraction_summary.json", summary)
    atomic_json(SNAPSHOT / "dry_run_summary.json", {
        "status": status,
        "validations": {"total": report["validation_count"], "passed": report["passed"], "failed": report["failed"]},
        "type_errors": report["type_errors"],
        "additional_controls": additional,
        "row_counts": {sheet: len(data[sheet]) for sheet in ctx["order"]},
        "leading_zero_sample": leading_zero_values[:20],
    })
    finalize_snapshot_checksums()
    if status != "PASS":
        raise RuntimeError("E1 DRY RUN failed")
    return read_json(SNAPSHOT / "dry_run_summary.json")


def google_retry(operation: Any, label: str) -> Any:
    last_error: Optional[Exception] = None
    for attempt in range(4):
        try:
            return operation()
        except Exception as exc:
            last_error = exc
            if attempt == 3:
                break
            response = getattr(exc, "response", None)
            if getattr(response, "status_code", None) == 429:
                time.sleep(GOOGLE_QUOTA_RESET_SECONDS)
            else:
                time.sleep(2 ** attempt)
    safe_detail = ""
    response = getattr(last_error, "response", None)
    if response is not None:
        try:
            payload = response.json()
            error = payload.get("error", {}) if isinstance(payload, dict) else {}
            safe_detail = " HTTP %s: %s" % (getattr(response, "status_code", ""), str(error.get("message") or "")[:500])
        except Exception:
            safe_detail = " HTTP %s" % getattr(response, "status_code", "")
    raise RuntimeError("Google Sheets operation failed after bounded retries: %s (%s)%s" % (label, type(last_error).__name__, safe_detail))


def read_matrices_chunked(
    spreadsheet: Any,
    sheet_names: Sequence[str],
    order: Sequence[str],
    headers: Dict[str, List[str]],
    row_counts: Dict[str, int],
) -> Dict[str, List[List[Any]]]:
    matrices: Dict[str, List[List[Any]]] = {}
    for source_name, logical_name in zip(sheet_names, order):
        width = len(headers[logical_name])
        total_rows = int(row_counts[logical_name]) + 1
        values: List[List[Any]] = []
        for start in range(0, total_rows, 5000):
            end = min(start + 5000, total_rows)
            range_name = "'%s'!A%d:%s%d" % (
                source_name.replace("'", "''"),
                start + 1,
                BASE.column_name(width),
                end,
            )
            response = google_retry(
                lambda range_name=range_name: spreadsheet.values_get(range_name, params={"valueRenderOption": "UNFORMATTED_VALUE"}),
                "read " + logical_name,
            )
            time.sleep(GOOGLE_READ_PACING_SECONDS)
            returned = response.get("values", [])
            expected_chunk_rows = end - start
            padded = [(row + [""] * (width - len(row)))[:width] for row in returned]
            if len(padded) < expected_chunk_rows:
                padded.extend([[""] * width for _ in range(expected_chunk_rows - len(padded))])
            values.extend(padded)
        while len(values) > 1 and all(value in (None, "") for value in values[-1]):
            values.pop()
        matrices[logical_name] = values
        print("read-back %s: %d business rows" % (logical_name, len(values) - 1), flush=True)
    return matrices


def clean_staging_sheets(spreadsheet: Any) -> None:
    stages = [worksheet for worksheet in spreadsheet.worksheets() if worksheet.title.startswith(STAGE_PREFIX)]
    if stages:
        google_retry(
            lambda: spreadsheet.batch_update({"requests": [{"deleteSheet": {"sheetId": worksheet.id}} for worksheet in stages]}),
            "clean stale E1 staging sheets",
        )


def create_staging_sheets(
    spreadsheet: Any,
    target_worksheets: Dict[str, Any],
    order: Sequence[str],
    headers: Dict[str, List[str]],
    row_counts: Dict[str, int],
) -> Tuple[List[str], Dict[str, int]]:
    stage_names = [STAGE_PREFIX + ("%02d" % index) for index in range(len(order))]
    add_requests = []
    for stage_name, logical_name in zip(stage_names, order):
        add_requests.append({
            "addSheet": {
                "properties": {
                    "title": stage_name,
                    "gridProperties": {
                        "rowCount": max(2, int(row_counts[logical_name]) + 1),
                        "columnCount": len(headers[logical_name]),
                        "frozenRowCount": 1,
                    },
                    "hidden": True,
                }
            }
        })
    response = google_retry(lambda: spreadsheet.batch_update({"requests": add_requests}), "create E1 staging sheets")
    replies = response.get("replies", [])
    if len(replies) != len(order):
        raise RuntimeError("Incomplete addSheet response for E1 staging")
    stage_ids = {
        logical_name: int(reply["addSheet"]["properties"]["sheetId"])
        for logical_name, reply in zip(order, replies)
    }
    format_requests = []
    for logical_name in order:
        target = target_worksheets[logical_name]
        stage_id = stage_ids[logical_name]
        width = len(headers[logical_name])
        rows = max(2, int(row_counts[logical_name]) + 1)
        format_requests.extend([
            {
                "copyPaste": {
                    "source": {"sheetId": target.id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": width},
                    "destination": {"sheetId": stage_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": width},
                    "pasteType": "PASTE_FORMAT",
                    "pasteOrientation": "NORMAL",
                }
            },
            {
                "setBasicFilter": {
                    "filter": {"range": {"sheetId": stage_id, "startRowIndex": 0, "endRowIndex": rows, "startColumnIndex": 0, "endColumnIndex": width}}
                }
            },
        ])
    google_retry(lambda: spreadsheet.batch_update({"requests": format_requests}), "prepare E1 staging formats")
    return stage_names, stage_ids


def upload_staging_values(
    spreadsheet: Any,
    stage_names: Sequence[str],
    order: Sequence[str],
    matrices: Dict[str, List[List[Any]]],
) -> Dict[str, Any]:
    pending: List[Dict[str, Any]] = []
    request_count = 0
    payload_bytes = 0
    written_rows = 0

    def flush() -> None:
        nonlocal pending, request_count, payload_bytes
        if not pending:
            return
        body = {"valueInputOption": "RAW", "data": pending}
        encoded_size = len(canonical_json(body))
        if encoded_size > MAX_VALUES_PAYLOAD:
            raise RuntimeError("Google values payload exceeds approved 1.5 MB implementation limit")
        google_retry(lambda body=body: spreadsheet.values_batch_update(body), "write E1 staging values")
        request_count += 1
        payload_bytes += encoded_size
        if request_count % 10 == 0:
            print("staging upload: %d requests, %.1f MB" % (request_count, payload_bytes / 1_000_000), flush=True)
        time.sleep(GOOGLE_WRITE_PACING_SECONDS)
        pending = []

    def add_values(stage_name: str, start: int, values: List[List[Any]]) -> None:
        nonlocal pending
        item = {"range": "'%s'!A%d" % (stage_name, start + 1), "values": values}
        single = {"valueInputOption": "RAW", "data": [item]}
        if len(canonical_json(single)) > MAX_VALUES_PAYLOAD:
            if len(values) <= 1:
                raise RuntimeError("One Google Sheets row exceeds the approved values payload limit")
            midpoint = len(values) // 2
            add_values(stage_name, start, values[:midpoint])
            add_values(stage_name, start + midpoint, values[midpoint:])
            return
        test = {"valueInputOption": "RAW", "data": pending + [item]}
        if pending and len(canonical_json(test)) > MAX_VALUES_PAYLOAD:
            flush()
        pending.append(item)

    for stage_name, logical_name in zip(stage_names, order):
        rows = matrices[logical_name]
        for start in range(0, len(rows), 500):
            values = rows[start:start + 500]
            add_values(stage_name, start, values)
            written_rows += len(values)
    flush()
    return {"request_count": request_count, "payload_bytes": payload_bytes, "written_rows_including_headers": written_rows}


def build_atomic_copy_requests(
    target_worksheets: Dict[str, Any],
    stage_ids: Dict[str, int],
    order: Sequence[str],
    headers: Dict[str, List[str]],
    row_counts: Dict[str, int],
) -> List[Dict[str, Any]]:
    requests = []
    for logical_name in order:
        target = target_worksheets[logical_name]
        stage_id = stage_ids[logical_name]
        data_rows = int(row_counts[logical_name]) + 1
        desired_rows = max(2, data_rows)
        width = len(headers[logical_name])
        if target.col_count < width:
            requests.append({"appendDimension": {"sheetId": target.id, "dimension": "COLUMNS", "length": width - target.col_count}})
        elif target.col_count > width:
            requests.append({"deleteDimension": {"range": {"sheetId": target.id, "dimension": "COLUMNS", "startIndex": width, "endIndex": target.col_count}}})
        if target.row_count < desired_rows:
            requests.append({"appendDimension": {"sheetId": target.id, "dimension": "ROWS", "length": desired_rows - target.row_count}})
        elif target.row_count > desired_rows:
            requests.append({"deleteDimension": {"range": {"sheetId": target.id, "dimension": "ROWS", "startIndex": desired_rows, "endIndex": target.row_count}}})
        requests.extend([
            {
                "copyPaste": {
                    "source": {"sheetId": stage_id, "startRowIndex": 0, "endRowIndex": data_rows, "startColumnIndex": 0, "endColumnIndex": width},
                    "destination": {"sheetId": target.id, "startRowIndex": 0, "endRowIndex": data_rows, "startColumnIndex": 0, "endColumnIndex": width},
                    "pasteType": "PASTE_NORMAL",
                    "pasteOrientation": "NORMAL",
                }
            },
            {
                "setBasicFilter": {
                    "filter": {"range": {"sheetId": target.id, "startRowIndex": 0, "endRowIndex": desired_rows, "startColumnIndex": 0, "endColumnIndex": width}}
                }
            },
            {"deleteSheet": {"sheetId": stage_id}},
        ])
    return requests


def invalid_atomic_request() -> Dict[str, Any]:
    return {"deleteSheet": {"sheetId": 2147483647}}


def load_e1_snapshot(label: str, require_baseline_match: bool) -> Dict[str, Any]:
    import gspread

    checksum_before = verify_snapshot_checksums()
    if checksum_before["status"] != "PASS":
        raise RuntimeError("Frozen E1 snapshot checksum verification failed")
    data, ctx = load_snapshot_data()
    local_validation = BASE.validate_fixture(data, ctx, output_path=None)
    if local_validation["status"] != "PASS" or local_validation["passed"] != 171:
        raise RuntimeError("Frozen E1 snapshot no longer passes 171 validations")
    order = ctx["order"]
    headers = ctx["headers"]
    dictionary = ctx["dictionary"]
    row_counts = {sheet: len(data[sheet]) for sheet in order}
    expected_matrices = BASE.fixture_matrices(data, order, headers)
    expected_state = BASE.state_from_matrices(expected_matrices, order, headers, dictionary)

    load_dotenv(ENV_FILE)
    client = gspread.service_account(filename=os.environ["GOOGLE_CREDENTIALS_PATH"])
    client.http_client.timeout = GOOGLE_HTTP_TIMEOUT
    spreadsheet = client.open_by_key(os.environ["RAW_COMPLETE_SPREADSHEET_ID"])
    clean_staging_sheets(spreadsheet)
    worksheet_list = spreadsheet.worksheets()
    if [worksheet.title for worksheet in worksheet_list] != order:
        raise RuntimeError("Live target schema/order changed before E1 load")
    target_worksheets = {worksheet.title: worksheet for worksheet in worksheet_list}
    baseline_matrices = read_matrices_chunked(spreadsheet, order, order, headers, {sheet: max(0, target_worksheets[sheet].row_count - 1) for sheet in order})
    baseline_state = BASE.state_from_matrices(baseline_matrices, order, headers, dictionary)
    if require_baseline_match and BASE.comparable_state(baseline_state) != BASE.comparable_state(expected_state):
        raise RuntimeError("Idempotency baseline differs from frozen E1 snapshot")

    stage_names: List[str] = []
    stage_ids: Dict[str, int] = {}
    load_dir = SNAPSHOT / "load"
    load_dir.mkdir(parents=True, exist_ok=True)
    try:
        stage_names, stage_ids = create_staging_sheets(spreadsheet, target_worksheets, order, headers, row_counts)
        upload_metrics = upload_staging_values(spreadsheet, stage_names, order, expected_matrices)
        stage_matrices = read_matrices_chunked(spreadsheet, stage_names, order, headers, row_counts)
        stage_state = BASE.state_from_matrices(stage_matrices, order, headers, dictionary)
        stage_matches = BASE.comparable_state(stage_state) == BASE.comparable_state(expected_state)
        if not stage_matches:
            raise RuntimeError("E1 staging read-back differs from normalized snapshot")

        copy_requests = build_atomic_copy_requests(target_worksheets, stage_ids, order, headers, row_counts)
        failure_type = None
        failure_status = None
        try:
            spreadsheet.batch_update({"requests": copy_requests + [invalid_atomic_request()], "includeSpreadsheetInResponse": False})
        except Exception as exc:
            failure_type = type(exc).__name__
            failure_status = getattr(getattr(exc, "response", None), "status_code", None)
        if failure_type is None:
            raise RuntimeError("Controlled E1 atomic failure unexpectedly succeeded")
        after_failure_matrices = read_matrices_chunked(spreadsheet, order, order, headers, {sheet: max(0, target_worksheets[sheet].row_count - 1) for sheet in order})
        after_failure_state = BASE.state_from_matrices(after_failure_matrices, order, headers, dictionary)
        failure_rollback_pass = BASE.comparable_state(after_failure_state) == BASE.comparable_state(baseline_state)
        if not failure_rollback_pass:
            raise RuntimeError("Controlled E1 failure changed the confirmed target baseline")

        google_retry(lambda: spreadsheet.batch_update({"requests": copy_requests, "includeSpreadsheetInResponse": False}), "atomic E1 server-side copy")
        final_worksheets = spreadsheet.worksheets()
        if [worksheet.title for worksheet in final_worksheets] != order:
            raise RuntimeError("Final live sheet order differs from contract")
        final_matrices = read_matrices_chunked(spreadsheet, order, order, headers, row_counts)
        final_state = BASE.state_from_matrices(final_matrices, order, headers, dictionary)
        final_matches = BASE.comparable_state(final_state) == BASE.comparable_state(expected_state)
        if not final_matches:
            raise RuntimeError("E1 final read-back differs from normalized snapshot")
        new_rows = sum(final_state["row_counts"][sheet] - baseline_state["row_counts"].get(sheet, 0) for sheet in order)
        result = {
            "status": "PASS",
            "label": label,
            "completed_at_utc": utc_now(),
            "snapshot_cutoff_at_utc": ctx["manifest"]["cutoff_at_utc"],
            "dry_run": {"status": local_validation["status"], "passed": local_validation["passed"], "total": local_validation["validation_count"]},
            "stage_read_back": "PASS",
            "google_full_load": "PASS",
            "read_back_validation": "PASS",
            "failure_rollback": {"status": "PASS", "safe_error_type": failure_type, "http_status": failure_status},
            "atomic_commit": {"status": "PASS", "request_count": len(copy_requests), "all_32_sheets_one_batch": True, "current_prices_and_stock_atomic": True},
            "upload_metrics": upload_metrics,
            "baseline_row_counts": baseline_state["row_counts"],
            "after_row_counts": final_state["row_counts"],
            "baseline_overall_checksum": baseline_state["overall_checksum"],
            "after_overall_checksum": final_state["overall_checksum"],
            "expected_overall_checksum": expected_state["overall_checksum"],
            "new_rows": new_rows,
            "pk_duplicates": final_state["pk_duplicate_count"],
            "fk_failures": final_state["fk_failure_count"],
            "guid_invalid": final_state["guid_invalid_count"],
            "headers_unchanged": not final_state["header_failures"],
            "leading_zero_06_preserved": bool(final_state["leading_zero_06_values"]),
            "snapshot_checksums": checksum_before,
        }
        atomic_json(load_dir / (label + ".json"), result)
        return result
    except Exception:
        try:
            clean_staging_sheets(spreadsheet)
        except Exception:
            pass
        raise


def finalize_e1_completion() -> Dict[str, Any]:
    preflight = read_json(E1_ROOT / "preflight_baseline.json")
    extraction = read_json(SNAPSHOT / "extraction_summary.json")
    dry_run = read_json(SNAPSHOT / "dry_run_summary.json")
    first_load = read_json(SNAPSHOT / "load" / "first_full_load.json")
    idempotency = read_json(SNAPSHOT / "load" / "same_snapshot_idempotency.json")
    checksum_after = verify_snapshot_checksums()
    complete = {
        "status": "PASS" if (
            preflight["status"] == "PASS"
            and dry_run["status"] == "PASS"
            and first_load["status"] == "PASS"
            and idempotency["status"] == "PASS"
            and idempotency["new_rows"] == 0
            and idempotency["pk_duplicates"] == 0
            and idempotency["fk_failures"] == 0
            and checksum_after["status"] == "PASS"
        ) else "FAIL",
        "completed_at_utc": utc_now(),
        "products": extraction["products"],
        "variants": extraction["variants"],
        "dry_run": dry_run["status"],
        "first_full_load": first_load["status"],
        "read_back_validation": first_load["read_back_validation"],
        "same_snapshot_idempotency": idempotency["status"],
        "idempotency_new_rows": idempotency["new_rows"],
        "idempotency_duplicates": idempotency["pk_duplicates"],
        "fk_failures": idempotency["fk_failures"],
        "snapshot_checksums": checksum_after,
    }
    atomic_json(SNAPSHOT / "load" / "e1_completion.json", complete)
    if complete["status"] != "PASS":
        raise RuntimeError("E1 completion criteria failed")
    return complete


def run_all() -> Dict[str, Any]:
    extraction_preflight(save=True)
    build_e1_snapshot()
    validate_e1_snapshot()
    gc.collect()
    load_e1_snapshot("first_full_load", require_baseline_match=False)
    gc.collect()
    load_e1_snapshot("same_snapshot_idempotency", require_baseline_match=True)
    return finalize_e1_completion()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["preflight", "extract", "validate", "load", "idempotency", "complete", "run-all"])
    args = parser.parse_args()
    if args.operation == "preflight":
        result = extraction_preflight(save=True)
    elif args.operation == "extract":
        result = build_e1_snapshot()
    elif args.operation == "validate":
        result = validate_e1_snapshot()
    elif args.operation == "load":
        result = load_e1_snapshot("first_full_load", require_baseline_match=False)
    elif args.operation == "idempotency":
        result = load_e1_snapshot("same_snapshot_idempotency", require_baseline_match=True)
    elif args.operation == "complete":
        result = finalize_e1_completion()
    else:
        result = run_all()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
