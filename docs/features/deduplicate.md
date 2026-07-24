<!-- last_verified: 2026-07-24 -->
# Feature: Deduplicate Before Ingest

## Purpose
Decide whether a candidate recording already exists in the catalog by fingerprinting it and matching it against the live index — before you commit it to the catalog.

## Used By
- UI: `/dedup` (`apps/web/src/components/dedup/dedup-view.tsx`)
- API: `POST /dedup/match` (multipart `file` OR form field `existing_key`, plus `sensitivity`)

## Core Functions
- `services/api/app/runtime/dedup.py` — `dedup_match_endpoint`
- `services/api/app/service/dedup.py` — `run_match()` (candidate → recognize → resolve → log)
- `services/api/app/repo/dejavu_index.py` — `recognize_matches()`
- `services/api/app/repo/b2_artifacts.py` — `put_json()` (result log), `get_inline_url()` (matched-track playback)

## Canonical Files
- Dedup orchestration: `services/api/app/service/dedup.py`

## Inputs
- file: `File` (WAV/MP3) — a new candidate, OR
- existing_key: string — an existing `catalog/` track to re-check
- sensitivity: `strict | balanced | loose`

## Outputs
- `DedupResult`: candidate_name, candidate_key, is_duplicate, sensitivity, threshold, top_match, matches[], matched_key, matched_title, matched_audio_url, created_at, result_key
- Side effects: a JSON verdict written to `results/dedup-<ts>.json` on B2

## Flow
- Client sends a candidate (uploaded file or existing catalog key) to `POST /dedup/match`
- For an existing key, the service downloads the object bytes from B2
- Service fingerprints the candidate to a temp file and calls `recognize_matches` (top 5)
- A candidate that *is* an existing catalog track excludes its own self-match
- Matches are resolved against the manifest (title/key); `is_duplicate` = top confidence ≥ the sensitivity threshold
- The matched track's inline playback URL is presigned; the full verdict is logged to `results/` on B2
- Response renders the verdict, the matched track (with an `<audio>` player), confidence and time-offset, and all matches

## Edge Cases
- Neither file nor existing_key provided → 400
- Non-audio upload → 415
- Empty index / no matches → `is_duplicate: false`, empty matches
- A match below the threshold → surfaced as a weak match but `is_duplicate: false`
- MySQL/Dejavu failure → 502

## UX States
- Source selector (Upload a file / Pick a catalog track) + sensitivity selector
- Running shows "Matching…"; result panel shows the verdict badge, matched track + player, and the match list
- Idle: prompt to run a check

## Verification
- Test files: `services/api/tests/test_dedup.py` (DedupResult mapping — duplicate, below-threshold, no-match; engine mocked)
- Required cases: duplicate flagged, weak match not flagged, no matches
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm build && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Audio Ingest](audio-ingest.md)
- [App Workflows](../app-workflows.md)
