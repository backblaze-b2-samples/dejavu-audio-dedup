<!-- last_verified: 2026-07-24 -->
# Feature: Fingerprint Index Export

## Purpose
Push the durable copy of the fingerprint index back to B2 so MySQL is never the only place the index lives: dump the MySQL fingerprint tables to `index/fingerprints.sql` and persist the per-track `index/manifest.json`.

## Used By
- API: `POST /index/export`
- (Called opportunistically by tooling/ops; the manifest is also maintained incrementally on every ingest/edit/delete.)

## Core Functions
- `services/api/app/runtime/index_export.py` — `export_index_endpoint`
- `services/api/app/service/index_export.py` — `export_index()`
- `services/api/app/repo/dejavu_index.py` — `dump_sql()` (DDL via `SHOW CREATE TABLE` + INSERTs), `fingerprint_count()`
- `services/api/app/repo/b2_artifacts.py` — `put_bytes()` (SQL dump), `put_json()` (manifest)

## Canonical Files
- Export orchestration: `services/api/app/service/index_export.py`
- SQL dump: `services/api/app/repo/dejavu_index.py::dump_sql`

## Inputs
- None (operates on the current MySQL index + manifest)

## Outputs
- `index/fingerprints.sql` on B2 — portable dump of the `songs` + `fingerprints` tables (DDL + rows; binary `hash` columns emitted as hex literals)
- `index/manifest.json` on B2 — re-saved with a fresh `updated_at`
- Response summary: `sql_dump_key`, `manifest_key`, `sql_dump_bytes`, `tracks`, `fingerprints`

## Flow
- `POST /index/export` → service re-saves the manifest, then calls `dump_sql()`
- `dump_sql()` reads the exact DDL for each Dejavu table and streams INSERT statements for every row (empty/header-only when nothing is fingerprinted yet)
- The dump is written to `index/fingerprints.sql`; the summary is returned
- To re-seed a fresh MySQL: `mysql dejavu < fingerprints.sql`

## Edge Cases
- No fingerprints yet → header-only dump (no tables), summary reports 0
- MySQL unreachable → 502

## Verification
- Test files: covered indirectly by `tests/test_manifest.py` (manifest shaping); the SQL dump requires a live MySQL (exercised in the end-to-end verify step)
- Quick verify command: `pnpm test:api`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md) — the two-index model
- [Audio Ingest](audio-ingest.md)
