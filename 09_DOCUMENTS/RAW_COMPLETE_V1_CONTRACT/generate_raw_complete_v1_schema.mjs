#!/usr/bin/env node

/**
 * Schema-only generator for the approved RAW COMPLETE v1 contract.
 *
 * Authoring: @oai/artifact-tool 2.8.6+
 * Compatibility finalization/verification: Python 3 with openpyxl
 *
 * The script reads only the approved contract files located beside it by
 * default. It does not access Google Sheets, OData, 1C, CURRENT RAW, or AI Seller.
 */

import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import crypto from "node:crypto";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const defaultOutputName = "RUKODELIE_AI_Product_Knowledge_Yarn_RAW_COMPLETE_v1.xlsx";

function parseArgs(argv) {
  const result = {
    contractDir: scriptDir,
    output: path.join(scriptDir, defaultOutputName),
    python: "python3",
    renderDir: "",
  };
  for (let index = 0; index < argv.length; index += 1) {
    const key = argv[index];
    const value = argv[index + 1];
    if (key === "--contract-dir" && value) result.contractDir = path.resolve(value);
    if (key === "--output" && value) result.output = path.resolve(value);
    if (key === "--python" && value) result.python = value;
    if (key === "--render-dir" && value) result.renderDir = path.resolve(value);
    if (["--contract-dir", "--output", "--python", "--render-dir"].includes(key)) index += 1;
  }
  return result;
}

const args = parseArgs(process.argv.slice(2));
const schemaVersion = "raw_complete_v1";
const expectedWorkbookName = "RUKODELIE AI Product Knowledge — RAW COMPLETE v1";

const requiredFiles = [
  "RAW_COMPLETE_V1_ARCHITECTURE.md",
  "RAW_COMPLETE_V1_DATA_DICTIONARY.csv",
  "RAW_COMPLETE_V1_ENTITYSET_MAPPING.csv",
  "RAW_COMPLETE_V1_ER_DIAGRAM.md",
  "RAW_COMPLETE_V1_IMPORT_PLAN.md",
  "RAW_COMPLETE_V1_VALIDATION_MATRIX.csv",
  "RAW_COMPLETE_V1_OPEN_QUESTIONS.md",
  "RAW_COMPLETE_V1_DECISION_REPORT.md",
  "RAW_COMPLETE_V1_REVISION_REPORT.md",
  "RAW_COMPLETE_V1_RED_TEAM_AUDIT.md",
  "RAW_COMPLETE_V1_FINAL_GO_NO_GO_AUDIT.md",
];

const sha256 = (value) => crypto.createHash("sha256").update(value).digest("hex");

function columnName(oneBased) {
  let value = oneBased;
  let result = "";
  while (value > 0) {
    const remainder = (value - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    value = Math.floor((value - 1) / 26);
  }
  return result;
}

async function loadCsvRows(fileName, sheetName) {
  const csvText = await fs.readFile(path.join(args.contractDir, fileName), "utf8");
  const workbook = await Workbook.fromCSV(csvText, { sheetName });
  const values = workbook.worksheets.getItem(sheetName).getUsedRange(true).values;
  const headers = values[0].map((value) => String(value ?? ""));
  return values.slice(1).map((row) => Object.fromEntries(headers.map((header, index) => [header, row[index] ?? ""])));
}

function parseFieldReference(value) {
  const text = String(value ?? "").trim();
  if (!text) return null;
  const match = text.match(/^(RAW_[A-Z0-9_]+)\.([A-Za-z0-9_]+)$/);
  return match ? { sheet: match[1], field: match[2] } : { invalid: text };
}

for (const fileName of requiredFiles) {
  await fs.access(path.join(args.contractDir, fileName));
}

const architectureText = await fs.readFile(path.join(args.contractDir, "RAW_COMPLETE_V1_ARCHITECTURE.md"), "utf8");
const architectureSheets = [];
for (const line of architectureText.split(/\r?\n/)) {
  const match = line.match(/^\| (TECHNICAL|METADATA|CORE|COMMERCIAL|MEDIA|CONTENT|MARKETPLACE|RELATIONS) \| (RAW_[A-Z0-9_]+) \|/);
  if (match) architectureSheets.push({ layer: match[1], sheet_name: match[2] });
}

const dictionaryRows = await loadCsvRows("RAW_COMPLETE_V1_DATA_DICTIONARY.csv", "DataDictionary");
const mappingRows = await loadCsvRows("RAW_COMPLETE_V1_ENTITYSET_MAPPING.csv", "EntitySetMapping");
const validationRows = await loadCsvRows("RAW_COMPLETE_V1_VALIDATION_MATRIX.csv", "ValidationMatrix");

const fieldsBySheet = new Map();
for (const row of dictionaryRows) {
  if (!fieldsBySheet.has(row.sheet_name)) fieldsBySheet.set(row.sheet_name, []);
  fieldsBySheet.get(row.sheet_name).push(row);
}

const dictionarySheetNames = [...fieldsBySheet.keys()];
const architectureSheetNames = architectureSheets.map((item) => item.sheet_name);
const fieldIndex = new Map(dictionaryRows.map((row) => [`${row.sheet_name}.${row.field_name}`, row]));
const preflightChecks = [];
const addCheck = (id, ok, evidence) => preflightChecks.push({ id, ok: Boolean(ok), evidence });

addCheck("required_contract_files_11", requiredFiles.length === 11, requiredFiles);
addCheck("physical_sheets_32", architectureSheetNames.length === 32 && dictionarySheetNames.length === 32, {
  architecture: architectureSheetNames.length,
  dictionary: dictionarySheetNames.length,
});
addCheck("physical_fields_466", dictionaryRows.length === 466, dictionaryRows.length);
addCheck("mappings_38", mappingRows.length === 38, mappingRows.length);
addCheck("validations_171", validationRows.length === 171, validationRows.length);
addCheck("sheet_order_exact", JSON.stringify(architectureSheetNames) === JSON.stringify(dictionarySheetNames), {
  architecture: architectureSheetNames,
  dictionary: dictionarySheetNames,
});
addCheck("sheet_names_unique", new Set(architectureSheetNames).size === architectureSheetNames.length, architectureSheetNames);
addCheck("sheet_names_excel_safe", architectureSheetNames.every((name) => name.length <= 31 && !/[\[\]:*?\\/]/.test(name)), architectureSheetNames);
addCheck("removed_sheets_absent", !architectureSheetNames.some((name) => ["RAW_PACKAGE_ITEMS", "RAW_STOCK_TOTALS", "RAW_PRICE_SNAPSHOT", "RAW_STOCK_BALANCES"].includes(name)), architectureSheetNames);

const duplicateHeaders = [];
for (const [sheetName, rows] of fieldsBySheet.entries()) {
  const names = rows.map((row) => String(row.field_name));
  const duplicates = names.filter((name, index) => names.indexOf(name) !== index);
  if (duplicates.length) duplicateHeaders.push({ sheet_name: sheetName, duplicates: [...new Set(duplicates)] });
}
addCheck("headers_unique_within_sheet", duplicateHeaders.length === 0, duplicateHeaders);
addCheck("unconfirmed_fields_zero", dictionaryRows.every((row) => !String(row.confirmed_status).includes("UNCONFIRMED_SOURCE")), dictionaryRows.filter((row) => String(row.confirmed_status).includes("UNCONFIRMED_SOURCE")).map((row) => `${row.sheet_name}.${row.field_name}`));
addCheck("field_contract_metadata_present", dictionaryRows.every((row) => ["sheet_name", "field_name", "data_type", "primary_key", "layer", "nullable", "source_entityset"].every((key) => String(row[key]).trim() !== "")), dictionaryRows.filter((row) => ["sheet_name", "field_name", "data_type", "primary_key", "layer", "nullable", "source_entityset"].some((key) => String(row[key]).trim() === "")).map((row) => `${row.sheet_name}.${row.field_name}`));
addCheck("mapping_targets_exist", mappingRows.every((row) => fieldsBySheet.has(row.target_sheet)), mappingRows.filter((row) => !fieldsBySheet.has(row.target_sheet)).map((row) => row.target_sheet));
addCheck("mapping_sources_declared", mappingRows.every((row) => String(row.source_system).trim() && String(row.source_entityset).trim() && String(row.source_role).trim()), mappingRows.filter((row) => !String(row.source_system).trim() || !String(row.source_entityset).trim() || !String(row.source_role).trim()));
addCheck("validation_ids_unique", new Set(validationRows.map((row) => row.validation_id)).size === validationRows.length, validationRows.map((row) => row.validation_id));
addCheck("validation_targets_exist", validationRows.every((row) => fieldsBySheet.has(row.target_sheet)), validationRows.filter((row) => !fieldsBySheet.has(row.target_sheet)).map((row) => ({ id: row.validation_id, target: row.target_sheet })));

const foreignKeyFailures = [];
for (const row of dictionaryRows) {
  const reference = parseFieldReference(row.foreign_key);
  if (!reference) continue;
  if (reference.invalid) {
    foreignKeyFailures.push({ source: `${row.sheet_name}.${row.field_name}`, reason: "invalid FK syntax", value: reference.invalid });
    continue;
  }
  const target = fieldIndex.get(`${reference.sheet}.${reference.field}`);
  if (!target) {
    foreignKeyFailures.push({ source: `${row.sheet_name}.${row.field_name}`, reason: "missing target", target: `${reference.sheet}.${reference.field}` });
    continue;
  }
  if (!String(target.primary_key).includes("YES") && !String(target.primary_key).includes("PART")) {
    foreignKeyFailures.push({ source: `${row.sheet_name}.${row.field_name}`, reason: "target is not key", target: `${reference.sheet}.${reference.field}` });
  }
  if (String(row.data_type) !== String(target.data_type)) {
    foreignKeyFailures.push({ source: `${row.sheet_name}.${row.field_name}`, reason: "type mismatch", source_type: row.data_type, target_type: target.data_type });
  }
}
addCheck("foreign_keys_resolve_and_types_match", foreignKeyFailures.length === 0, foreignKeyFailures);

const preflightFailures = preflightChecks.filter((item) => !item.ok);
if (preflightFailures.length > 0) {
  console.error(JSON.stringify({ status: "PREFLIGHT_FAILED", failures: preflightFailures }, null, 2));
  process.exit(2);
}

const sheetSchemas = architectureSheets.map(({ layer, sheet_name }) => {
  const fields = fieldsBySheet.get(sheet_name).map((row) => String(row.field_name));
  return { layer, sheet_name, fields, field_count: fields.length };
});
const totalFields = sheetSchemas.reduce((sum, schema) => sum + schema.field_count, 0);

const workbook = Workbook.create();
for (const schema of sheetSchemas) {
  const sheet = workbook.worksheets.add(schema.sheet_name);
  const lastColumn = columnName(schema.field_count);
  const headerRange = sheet.getRange(`A1:${lastColumn}1`);
  headerRange.values = [schema.fields];
  headerRange.format = {
    fill: "#1F4E78",
    font: { bold: true, color: "#FFFFFF" },
    horizontalAlignment: "left",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: "#163A5C" },
  };
  headerRange.format.rowHeightPx = 36;
  headerRange.format.columnWidthPx = 165;

  const table = sheet.tables.add(`A1:${lastColumn}1`, true, `T_${schema.sheet_name}`);
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;
  table.showBandedRows = false;
  sheet.freezePanes.freezeRows(1);
}

await fs.mkdir(path.dirname(args.output), { recursive: true });
const exported = await SpreadsheetFile.exportXlsx(workbook);
await exported.save(args.output);

const schemaDefinition = {
  workbook_name: expectedWorkbookName,
  schema_version: schemaVersion,
  sheets: sheetSchemas,
  total_fields: totalFields,
};
const schemaJsonPath = path.join(os.tmpdir(), `raw_complete_v1_schema_${process.pid}.json`);
await fs.writeFile(schemaJsonPath, JSON.stringify(schemaDefinition), "utf8");

const openpyxlCode = String.raw`
import json
import sys
from openpyxl import load_workbook

xlsx_path, schema_path = sys.argv[1], sys.argv[2]
with open(schema_path, "r", encoding="utf-8") as handle:
    schema = json.load(handle)

wb = load_workbook(xlsx_path, read_only=False, data_only=False)
expected_names = [item["sheet_name"] for item in schema["sheets"]]
if wb.sheetnames != expected_names:
    raise AssertionError({"sheet_order": {"expected": expected_names, "actual": wb.sheetnames}})

for item in schema["sheets"]:
    ws = wb[item["sheet_name"]]
    ws.freeze_panes = "A2"
wb.save(xlsx_path)

wb = load_workbook(xlsx_path, read_only=False, data_only=False)
checks = []
def add_check(check_id, ok, evidence):
    checks.append({"id": check_id, "ok": bool(ok), "evidence": evidence})

add_check("openpyxl_sheet_count_32", len(wb.sheetnames) == 32, len(wb.sheetnames))
add_check("openpyxl_sheet_order_exact", wb.sheetnames == expected_names, wb.sheetnames)
total_headers = 0
sheet_results = []
for item in schema["sheets"]:
    ws = wb[item["sheet_name"]]
    actual_headers = [ws.cell(row=1, column=index + 1).value for index in range(len(item["fields"]))]
    nonempty_below = [cell.coordinate for row in ws.iter_rows(min_row=2) for cell in row if cell.value is not None]
    formulas = [cell.coordinate for row in ws.iter_rows() for cell in row if cell.data_type == "f"]
    has_filter = bool(ws.auto_filter.ref) or bool(ws.tables)
    total_headers += len(actual_headers)
    sheet_results.append({
        "sheet_name": item["sheet_name"],
        "headers_exact": actual_headers == item["fields"],
        "header_count": len(actual_headers),
        "no_data_below_header": len(nonempty_below) == 0,
        "formula_count": len(formulas),
        "freeze_panes": str(ws.freeze_panes),
        "filter_present": has_filter,
        "max_row": ws.max_row,
    })

add_check("openpyxl_headers_466", total_headers == 466, total_headers)
add_check("openpyxl_headers_exact", all(item["headers_exact"] for item in sheet_results), [item for item in sheet_results if not item["headers_exact"]])
add_check("openpyxl_only_header_row", all(item["no_data_below_header"] and item["max_row"] == 1 for item in sheet_results), [item for item in sheet_results if not item["no_data_below_header"] or item["max_row"] != 1])
add_check("openpyxl_no_formulas", all(item["formula_count"] == 0 for item in sheet_results), [item for item in sheet_results if item["formula_count"]])
add_check("openpyxl_freeze_first_row", all(item["freeze_panes"] == "A2" for item in sheet_results), [item for item in sheet_results if item["freeze_panes"] != "A2"])
add_check("openpyxl_filters_present", all(item["filter_present"] for item in sheet_results), [item for item in sheet_results if not item["filter_present"]])

failures = [item for item in checks if not item["ok"]]
print(json.dumps({"checks": checks, "sheet_results": sheet_results, "failures": failures}, ensure_ascii=False))
if failures:
    sys.exit(3)
`;

const pythonResult = spawnSync(args.python, ["-c", openpyxlCode, args.output, schemaJsonPath], {
  encoding: "utf8",
  maxBuffer: 16 * 1024 * 1024,
});
await fs.unlink(schemaJsonPath).catch(() => {});
if (pythonResult.status !== 0) {
  console.error(pythonResult.stderr || pythonResult.stdout || `openpyxl exited with ${pythonResult.status}`);
  process.exit(3);
}
const openpyxlQa = JSON.parse(pythonResult.stdout);

const finalWorkbook = await SpreadsheetFile.importXlsx(await FileBlob.load(args.output));
const finalSheetNames = finalWorkbook.worksheets.items.map((sheet) => sheet.name);
const finalChecks = [];
const addFinalCheck = (id, ok, evidence) => finalChecks.push({ id, ok: Boolean(ok), evidence });
addFinalCheck("artifact_reopen_sheet_count_32", finalSheetNames.length === 32, finalSheetNames.length);
addFinalCheck("artifact_reopen_sheet_order_exact", JSON.stringify(finalSheetNames) === JSON.stringify(architectureSheetNames), finalSheetNames);

let reopenedHeaderCount = 0;
let reopenedDataRows = 0;
let reopenedFormulas = 0;
for (const schema of sheetSchemas) {
  const sheet = finalWorkbook.worksheets.getItem(schema.sheet_name);
  const lastColumn = columnName(schema.field_count);
  const headers = sheet.getRange(`A1:${lastColumn}1`).values[0].map((value) => String(value ?? ""));
  const secondRow = sheet.getRange(`A2:${lastColumn}2`).values[0];
  const formulas = sheet.getRange(`A1:${lastColumn}2`).formulas.flat();
  reopenedHeaderCount += headers.length;
  if (secondRow.some((value) => value !== null && value !== undefined && String(value) !== "")) reopenedDataRows += 1;
  reopenedFormulas += formulas.filter((value) => value !== null && value !== undefined && String(value) !== "").length;
  addFinalCheck(`headers_exact:${schema.sheet_name}`, JSON.stringify(headers) === JSON.stringify(schema.fields), headers);
}
addFinalCheck("artifact_reopen_headers_466", reopenedHeaderCount === 466, reopenedHeaderCount);
addFinalCheck("artifact_reopen_no_data_rows", reopenedDataRows === 0, reopenedDataRows);
addFinalCheck("artifact_reopen_no_formulas", reopenedFormulas === 0, reopenedFormulas);

if (args.renderDir) {
  await fs.mkdir(args.renderDir, { recursive: true });
  for (let index = 0; index < sheetSchemas.length; index += 1) {
    const schema = sheetSchemas[index];
    const previewLastColumn = columnName(Math.min(schema.field_count, 8));
    const preview = await finalWorkbook.render({
      sheetName: schema.sheet_name,
      range: `A1:${previewLastColumn}2`,
      scale: 1,
      format: "png",
    });
    await fs.writeFile(
      path.join(args.renderDir, `${String(index + 1).padStart(2, "0")}_${schema.sheet_name}.png`),
      new Uint8Array(await preview.arrayBuffer()),
    );
  }
  addFinalCheck("rendered_all_32_sheets", (await fs.readdir(args.renderDir)).filter((name) => name.endsWith(".png")).length === 32, args.renderDir);
}

const finalFailures = [...openpyxlQa.failures, ...finalChecks.filter((item) => !item.ok)];
const schemaSerialization = JSON.stringify(schemaDefinition);
const summary = {
  status: finalFailures.length === 0 ? "PASS" : "FAILED",
  output: args.output,
  counts: {
    sheets: sheetSchemas.length,
    fields: totalFields,
    mappings: mappingRows.length,
    validations: validationRows.length,
    data_rows: 0,
    formulas: 0,
  },
  schema_checksum_sha256: sha256(Buffer.from(schemaSerialization, "utf8")),
  schema_serialization: "UTF-8 minified JSON; ordered keys as emitted by JSON.stringify; workbook_name, schema_version, ordered sheets with ordered fields, total_fields",
  preflight_checks: preflightChecks,
  openpyxl_checks: openpyxlQa.checks,
  final_checks: finalChecks,
  failures: finalFailures,
};
console.log(JSON.stringify(summary, null, 2));
if (finalFailures.length > 0) process.exit(4);
