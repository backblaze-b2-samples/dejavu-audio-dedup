<!-- last_verified: 2026-07-24 -->
# Feature: Catalog Explorer

## Purpose
An app-scoped view of the ingested audio catalog — the objects under the `catalog/` prefix — with fingerprint status, inline playback, and the full Track lifecycle (read / edit / delete). Complementary to the full-bucket [File Browser](file-browser.md).

## Used By
- UI: `/catalog` (list, `catalog-table.tsx`) and `/catalog/[key]` (detail, `track-detail.tsx` + `edit-track-form.tsx`)
- API: `GET /catalog`, `GET /catalog-item?key=`, `PATCH /catalog-item?key=`, `DELETE /catalog-item?key=`

## Core Functions
- `services/api/app/runtime/catalog.py` — list / get / edit / delete endpoints
- `services/api/app/service/catalog.py` — `list_tracks()`, `get_track()`, `edit_track()`, `delete_track()`
- `services/api/app/service/manifest.py` — the metadata source of truth on B2
- `apps/web/src/lib/queries.ts` — `useCatalog`, `useTrack`, `useUpdateTrack`, `useDeleteTrack`

## Canonical Files
- Track service: `services/api/app/service/catalog.py`
- Catalog list UI: `apps/web/src/components/catalog/catalog-table.tsx`

## Inputs
- key: string (a `catalog/` object key — sent as a query parameter; validated against the prefix + traversal patterns)
- TrackUpdate (PATCH body): title, artist, notes, canonical_status, duplicate_of

## Outputs
- `GET /catalog` → `Track[]` (joined with the manifest, newest-first, each with a presigned inline `audio_url`)
- `GET /catalog-item?key=` → `TrackDetail`
- `PATCH /catalog-item?key=` → `TrackDetail` (manifest updated; audio bytes immutable)
- `DELETE /catalog-item?key=` → `{ deleted, key }` (B2 object removed **scoped to `catalog/`**, MySQL fingerprints dropped, manifest entry removed)

## Flow
- List page fetches `GET /catalog` → renders each track with title/artist, duration, fingerprint status/canonical badge, and an inline `<audio>` player
- A track with a manifest `track_id` shows **Fingerprinted**; one present on B2 but not the manifest shows **Pending**; a flagged one shows **Duplicate**
- Detail page fetches `GET /catalog-item?key=` → metadata, player, and a pre-filled edit form; edit uses a **selector** for canonical status
- Delete confirms via an `AlertDialog`, then removes the object (scoped to `catalog/`), drops fingerprints, and updates the manifest

## Edge Cases
- Key outside `catalog/` or containing traversal → 400
- Missing track → 404
- Delete when the track was never fingerprinted (no `track_id`) → object + manifest removed, no MySQL drop

## UX States
- Empty: prompt to ingest a track
- Loading: skeletons
- Error: inline error with retry
- Loaded: track rows with players + actions; detail with player, metadata, and edit form

## Verification
- Test files: `services/api/tests/test_catalog.py`
- Required cases: fingerprinted vs pending shaping, catalog-key prefix rejection
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm build && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [File Browser](file-browser.md)
- [Audio Ingest](audio-ingest.md)
