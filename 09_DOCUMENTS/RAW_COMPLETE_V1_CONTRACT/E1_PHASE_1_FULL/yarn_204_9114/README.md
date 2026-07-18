# E1 Phase 1 Full — local dataset and Git evidence

E1 completed for 204 products and 9,114 variants at cutoff
`2026-07-18T17:49:40Z` with 175,098 business rows.

The complete `raw/` checkpoints and 32 `normalized/` CSV files are retained
locally and in the verified E1 ZIP backup. They are intentionally excluded
from Git because they are generated data artifacts totaling approximately
919 MiB.

Git tracks only compact completion evidence:

- `manifest.json`;
- `row_counts.json`;
- `source_exclusions.json`;
- `checksums.sha256`;
- `dry_run_summary.json`;
- `validation_results.json`;
- `load/e1_completion.json`;
- `load/first_full_load.json`;
- `load/same_snapshot_idempotency.json`.

The checksum manifest continues to describe the full local E1 artifact set.
No credentials, Base64 payloads, ZIP files, or XLSX backups belong in Git.
