<!-- last_verified: 2026-07-15 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Dashboard with dedup metrics, ingest-activity chart, recent ingests
  - Catalog: ingest WAV/MP3, browse tracks with inline playback + fingerprint status, edit/delete
  - Deduplicate: match a candidate against the live index, view the verdict
  - Bucket explorer (Files) + generic Upload — the reusable B2-backed scaffolding
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - REST API for catalog ingest/list/detail/edit/delete, dedup match, index export
  - B2 S3 integration via boto3 (raw audio + SQL dump + manifest + result logs)
  - Dejavu acoustic fingerprinting into a MySQL index (contained in `repo/dejavu_index.py`)
  - Audio-stream metadata extraction (mutagen)
  - Health check, structured JSON logging, Prometheus-format metrics
- **packages/shared/** — TypeScript type definitions
  - Mirrors Pydantic models from the API
  - Consumed by `apps/web/` as workspace dependency
- **infra/docker-compose.yml** — MySQL 8 fingerprint database (Dejavu's backend)

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Each file stays under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (FileMetadata, UploadStats, etc.)
    config/                Settings loaded from environment
    repo/                  B2 S3 client (data access layer)
    service/               Business logic (upload, files, metadata)
    runtime/               FastAPI route handlers
  tests/                   pytest tests (structural + integration)
```

## Boundary Invariants

- **No external SDK leakage**: `boto3` is only imported in `app/repo/`. All other layers interact with B2 through the repo interface.
- **No raw dicts at boundaries**: All data crossing layer boundaries uses typed Pydantic models.
- **No cross-layer mutable state**: Configuration is read-only after init, and no mutable state is shared *between* layers. Intra-layer caches/counters (the listing cache in `repo/b2_client.py`, the download counter in `repo/counter.py`, the rate-limit and metrics state in `runtime/`) are module-local and guarded by a `threading.Lock`.
- **Validated inputs**: All HTTP inputs validated by FastAPI/Pydantic. File keys reject empty and path-traversal patterns; optional prefix confinement via `ALLOWED_KEY_PREFIX` (off by default).

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently`
  - Web: `localhost:3000`
  - API: `localhost:8000`
- **Railway** — two services from the same repo
  - See `infra/railway/README.md` for configuration

## Data Stores — the two-index model

This app deliberately has **two** stores with distinct roles:

- **Backblaze B2** (S3-compatible) — the **durable source of truth**. Holds:
  - `catalog/<track>` — raw ingested audio (immutable bytes)
  - `index/manifest.json` — the per-track metadata source of truth (title, artist, notes, canonical/duplicate label, fingerprint id + count, extracted stream properties). Catalog objects hold only audio bytes; everything editable lives here.
  - `index/fingerprints.sql` — a portable dump of the MySQL fingerprint tables
  - `results/dedup-<ts>.json` — an auditable log of every dedup run
- **MySQL** (Dejavu's canonical backend) — the **live, queryable index**. Populated at ingest; what Dejavu matches candidates against. It is *derived* state: it can be dropped and re-seeded from `index/fingerprints.sql` on B2.

Dejavu never queries B2 directly. "Match against the B2-stored index" means: restore the dump into MySQL, then query. Represent both layers honestly — the durable copy on B2, the live copy in MySQL.

## External Services

- **Backblaze B2 S3 API** — durable storage of audio + fingerprint artifacts, presigned playback URLs
- **MySQL** — Dejavu fingerprint index (local via `infra/docker-compose.yml`)
- **Dejavu** — local, in-process acoustic fingerprinting (no external API, no key)

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins. `CORSMiddleware` is registered LAST in `main.py` (outermost) so it wraps **every** response, including uncaught-exception 500s — otherwise the browser would block error responses and the UI would only see an opaque "network error". See [docs/RELIABILITY.md](docs/RELIABILITY.md#error-handling). A per-IP rate-limit middleware sits inner to CORS; see [docs/SECURITY.md](docs/SECURITY.md#rate-limiting).
- **API -> B2** — authenticated via application keys, signature v4
- **Client -> B2** — presigned URLs for download (10-min expiry, forced attachment)

## Data Flows

- **Ingest**: Browser -> `POST /catalog/ingest` (multipart) -> service stores audio to `catalog/` on B2 -> writes bytes to a temp file -> `dejavu_index.fingerprint_file` populates MySQL -> pre-ingest dedup check -> manifest updated on B2 -> `IngestResponse`
- **Deduplicate**: Browser -> `POST /dedup/match` (candidate file OR `existing_key`) -> service fingerprints the candidate -> `dejavu_index.recognize_matches` queries MySQL -> verdict resolved against the manifest -> result logged to `results/` on B2 -> `DedupResult`
- **Index export**: Browser -> `POST /index/export` -> `dejavu_index.dump_sql` -> `index/fingerprints.sql` + `index/manifest.json` written to B2
- **Catalog read**: Browser -> `GET /catalog` / `GET /catalog-item?key=` -> service joins the `catalog/` object listing with the manifest, presigns inline audio URLs
- **Edit**: Browser -> `PATCH /catalog-item?key=` -> manifest entry updated (audio bytes immutable)
- **Delete**: Browser -> `DELETE /catalog-item?key=` -> repo deletes the B2 object (scoped to `catalog/`) -> `dejavu_index.drop_track` removes its MySQL fingerprints -> manifest entry removed

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (logs duration per request; also the catch-all that converts uncaught exceptions to a typed JSON 500)
- `/metrics` endpoint (Prometheus format: request count, latency, upload count)
- `/health` endpoint (B2 connectivity check)

## Canonical Files

- Fingerprint engine + MySQL (contained): `services/api/app/repo/dejavu_index.py`
- Track lifecycle service: `services/api/app/service/catalog.py`
- Dedup service: `services/api/app/service/dedup.py`
- Manifest shaping (B2 metadata source of truth): `services/api/app/service/manifest.py`
- B2 artifact writes: `services/api/app/repo/b2_artifacts.py`
- Layered API handlers: `services/api/app/runtime/catalog.py`, `dedup.py`, `index_export.py`
- Pydantic models: `services/api/app/types/` (`catalog.py`, `dedup.py`, `files.py`, ...)
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`
- Frontend API client: `apps/web/src/lib/api-client.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Audio Ingest & Fingerprinting](docs/features/audio-ingest.md)
- [Deduplicate Before Ingest](docs/features/deduplicate.md)
- [Catalog Explorer](docs/features/catalog.md)
- [Fingerprint Index Export](docs/features/fingerprint-index.md)
- [File Browser](docs/features/file-browser.md)
- [File Upload](docs/features/file-upload.md)
- [Dashboard](docs/features/dashboard.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
