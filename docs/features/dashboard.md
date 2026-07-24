<!-- last_verified: 2026-07-24 -->
# Feature: Dashboard

## Purpose
An at-a-glance view of the dedup pipeline: how big the catalog is, how much has been fingerprinted, and how many duplicates were caught.

## Used By
- UI: `/` (dashboard home)
- API: `GET /catalog/stats`, `GET /catalog/stats/activity`, `GET /catalog`

## Core Functions
- `apps/web/src/components/dashboard/stats-cards.tsx` — 4 stat cards
- `apps/web/src/components/dashboard/upload-chart.tsx` — ingest-activity bar chart (last 7 days)
- `apps/web/src/components/dashboard/recent-uploads-table.tsx` — recent ingests table
- `apps/web/src/lib/queries.ts` — `useCatalogStats()`, `useIngestActivity()`, `useCatalog()`
- `services/api/app/service/catalog.py` — `get_catalog_stats()`, `get_ingest_activity()`

## Canonical Files
- Stats service logic: `services/api/app/service/catalog.py`
- Stat cards: `apps/web/src/components/dashboard/stats-cards.tsx`

## Inputs
- None (dashboard loads data automatically)

## Outputs
- `GET /catalog/stats` → `CatalogStats` (tracks_in_catalog, fingerprints_indexed, duplicates_detected, duplicate_pct, total_audio_bytes, total_audio_human)
- `GET /catalog/stats/activity?days=7` → `DailyIngestCount[]` (ingests per day, from manifest `ingested_at`)
- `GET /catalog` (sliced) → recent `Track[]`

## Flow
- Page loads → parallel calls for stats, ingest activity, and the catalog list
- Stat cards: Tracks in Catalog, Fingerprints Indexed, Duplicates Detected (count + %), Audio on B2
- Ingest chart: server-aggregated daily fingerprint counts for the last 7 days
- Recent ingests table: latest tracks with title, length, date, and status badge (Fingerprinted / Pending / Duplicate)

## Edge Cases
- API unavailable → inline error states with retry
- Empty catalog → empty chart + table messages, zeroed cards
- Fingerprint count falls back to the manifest sum if MySQL is briefly unreachable

## UX States
- Loading: skeletons for cards, chart, table
- Empty: "No tracks yet" / "No ingests yet"
- Loaded: populated cards, chart, table

## Verification
- Test files: `services/api/tests/test_catalog.py`
- Required cases: stats with tracks, empty catalog, activity aggregation
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm build && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Catalog Explorer](catalog.md)
- [App Workflows](../app-workflows.md)
