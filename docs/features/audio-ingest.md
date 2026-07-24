<!-- last_verified: 2026-07-24 -->
# Feature: Audio Ingest & Fingerprinting

## Purpose
Add a WAV/MP3 recording to the catalog: store it durably on B2, fingerprint it locally with Dejavu into the live MySQL index, and record its metadata in the B2 manifest.

## Used By
- UI: `/catalog` — the "Ingest track" dialog (`apps/web/src/components/catalog/ingest-form.tsx`)
- API: `POST /catalog/ingest` (multipart: `file`, `title`, `artist`, `sensitivity`)

## Core Functions
- `services/api/app/runtime/catalog.py` — `ingest_endpoint` (streamed read + size guard)
- `services/api/app/service/catalog.py` — `ingest_track()` (validate → store → fingerprint → manifest)
- `services/api/app/repo/dejavu_index.py` — `fingerprint_file()`, `recognize_file()` (the only dejavu/MySQL caller)
- `services/api/app/service/audio_metadata.py` — `extract_audio_stream()` (mutagen)
- `services/api/app/service/manifest.py` — manifest load/upsert/save
- `services/api/app/repo/b2_client.py` — `upload_file()`; `repo/b2_artifacts.py` — `put_json()` (manifest)

## Canonical Files
- Ingest orchestration: `services/api/app/service/catalog.py`
- Fingerprint engine: `services/api/app/repo/dejavu_index.py`

## Inputs
- file: `File` (WAV or MP3, multipart)
- title: string (optional; defaults to the sanitized filename)
- artist: string (optional)
- sensitivity: `strict | balanced | loose` (maps to a Dejavu confidence threshold)

## Outputs
- `IngestResponse`: key, track_id, fingerprint_count, duration_seconds, is_duplicate, matched_key, matched_title, confidence, message
- Side effects: audio stored at `catalog/<name>` on B2; fingerprints inserted into MySQL; `index/manifest.json` updated on B2

## Flow
- Client uploads the file to `POST /catalog/ingest`
- API streams the body with a 100MB guard, validates audio type + magic bytes
- Service stores the bytes at `catalog/<sanitized_name>` on B2
- Service extracts stream metadata (duration/sample rate/channels/bitrate) via mutagen
- Service writes the bytes to a temp file and **recognizes it against the existing index first** (so it can't match itself) — a match above the sensitivity threshold flags `is_duplicate` and labels the track `duplicate`
- Service fingerprints the file into MySQL (`song_name = catalog key`) and reads back the track id + fingerprint count
- Service upserts the manifest entry and saves it to B2
- Temp file is always cleaned up

## Edge Cases
- Non-audio / wrong magic bytes → 415
- Empty file → 400
- File > 100MB → 413
- MySQL/Dejavu/pydub failure (e.g. MP3 with no ffmpeg on host) → 502 (EngineError)
- Re-ingest of an existing recording → stored + fingerprinted, but flagged `duplicate` with `duplicate_of` set

## UX States
- Dialog form with file picker, title (with hint), artist, and a **sensitivity selector** (default Balanced)
- Submitting shows "Fingerprinting…"; success/duplicate surfaced as a toast
- On success the catalog list + dashboard invalidate and re-fetch

## Verification
- Test files: `services/api/tests/test_catalog.py` (Track shaping, key scoping), `tests/test_manifest.py` (manifest shaping)
- Required cases: fingerprinted vs pending status, key-prefix rejection, manifest upsert/merge/remove
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm build && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: all pytest tests green, no ruff violations

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Deduplicate](deduplicate.md)
- [Catalog Explorer](catalog.md)
- [App Workflows](../app-workflows.md)
