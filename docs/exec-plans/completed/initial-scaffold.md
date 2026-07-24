# Build plan — `dejavu-audio-dedup`

Source of truth for the starter tree: `.claude/scratch/vcsk-6c8a9c0a-810c-4692-a74f-82076757185e/`
(cloned fresh in Phase 0). Every keep/trim/add below is a delta against **that** tree.

---

## 1. Purpose

`dejavu-audio-dedup` is a B2 sample for **audio-catalog deduplication at scale**. Music
streaming platforms and podcast networks ingest large raw audio libraries (WAV/MP3),
and before adding a track to the catalog they need to know: *have we seen this recording
already?* This app demonstrates the pattern end to end using **[Dejavu](https://github.com/worldveil/dejavu)**,
the OSS acoustic-fingerprinting library, as the local matching engine:

- **B2 is the durable storage layer** for both the raw audio catalog **and** every derived
  fingerprint artifact — the SQL fingerprint dump, the per-track JSON manifest, and the
  dedup result logs. Nothing app-specific lives outside B2 except the live queryable index.
- **Dejavu runs locally** (no external API, no second key — B2 credentials only): it reads
  each audio file, computes spectrogram-peak fingerprint hashes, and populates a **MySQL**
  fingerprint database (the vendor's canonical backend). New candidate tracks are
  fingerprinted and matched against that index; duplicates are flagged and logged to B2.

Audience: data/metadata engineers building ingest pipelines who want a working reference for
"fingerprint locally, store everything on B2, dedup before ingest."

---

## 2. Architecture delta from `vibe-coding-starter-kit`

The starter kit is the ceiling. Keep the full-stack scaffold (layered FastAPI, shadcn UI kit,
TanStack Query data layer, structural tests, doctor preflight, JSON logging, `/health`+`/metrics`)
and strip what an audio-dedup app doesn't need.

### KEEP (as-is — do not strip, rename semantics, or replace)
- **UI kit / design system** — `apps/web/src/components/ui/`, tokens in `globals.css`, `/design` page. Build new screens from these primitives.
- **Bucket explorer (File Explorer) — NON-NEGOTIABLE KEEP.** `/files` route, `apps/web/src/app/files/`, `apps/web/src/components/files/`, its sidebar entry. This is the full-bucket browse over *all* objects (raw audio + SQL dumps + manifests + results). It is never removable.
- **Upload page** — `/upload` route + `apps/web/src/components/upload/`. Kept as the generic B2-backed upload surface (the audio-specific ingest is a *separate* add, see below). Sidebar entry stays.
- **Layered backend** (`types → config → repo → service → runtime`), structural tests, `repo/counter.py`, ratelimit, metrics, health, CORS-on-errors middleware ordering, single-root-`.env` loading.
- **The audio upload path already exists**: `service/upload.py` `ALLOWED_TYPES` already includes `audio/mpeg` and `audio/wav` with magic-byte validation (`ID3`/frame-sync for MP3, `RIFF…WAVE` for WAV). Reuse it — don't reinvent MIME validation.

### TRIM (remove from starter)
- **Image/PDF/EXIF metadata extraction** — `service/metadata.py` image + PDF branches are not this app's domain. Replace with **audio metadata** (duration, sample rate, channels, bitrate) via a lightweight pure-Python lib (`mutagen`). Drop `Pillow` + `PyPDF2` from `requirements.txt`.
- **Generic dashboard defaults** — `components/dashboard/` stats/chart/table get *replaced* (see §Key features) with dedup metrics. (Adapt, not delete — the Dashboard route stays.)
- **Donor screenshots** — `docs/images/` is already empty (fetch strips donor `b2-starterkit-*` PNGs). README image refs must be repointed to sample-named paths that **sample-4-screenshot** will fill later. **Do NOT create any images in this step.**
- **Starter exec-plans history** — `docs/exec-plans/completed/*` starter entries are the starter's history; the scaffold plan replaces them (Phase 5 moves this plan into `docs/exec-plans/completed/initial-scaffold.md`).

### ADD (new for `dejavu-audio-dedup`)
- **Sample-specific asset explorer — Catalog / Library view** (`/catalog`): the mandated app-scoped explorer, listing only objects under the **`catalog/`** prefix (the ingested audio tracks) with per-track fingerprint status (fingerprinted / pending), duration, and an inline `<audio>` player. This is distinct from and complementary to the non-negotiable full-bucket `/files` explorer.
- **Deduplicate / Match view** (`/dedup`): the marquee workflow. Upload a candidate track (or pick an existing catalog track), fingerprint it, match against the live index, and show `is_duplicate`, the matched canonical track, confidence, and time-offset. Every run is logged to B2 under `results/`.
- **Dejavu engine module** — `repo/dejavu_index.py`: the **only** module that imports `dejavu` and the MySQL driver. Mirrors the "boto3-only-in-repo" containment rule (see §5 invariant).
- **MySQL fingerprint DB via Docker Compose** — `infra/docker-compose.yml` (a `mysql:8` service). Dejavu's canonical backend; `.local` has Colima/Docker. Connection via **non-B2** env vars (`FP_DB_HOST/PORT/USER/PASSWORD/NAME`).
- **Dedup dashboard** — new `components/dashboard/` widgets (see §Key features).

---

## 3. B2 surface (S3-compatible only — no b2-native)

All operations go through `repo/b2_client.py` / `repo/b2_object.py` using the S3 API with a
custom user-agent (`user_agent_extra="dejavu-audio-dedup"`) and `signature_version="s3v4"`.
No b2-native SDK anywhere.

| S3 op | Where it's used |
|-------|-----------------|
| `PutObject` | raw audio ingest → `catalog/<track>`; SQL dump → `index/fingerprints.sql`; per-track manifest → `index/manifest.json`; dedup result logs → `results/dedup-<ts>.json` |
| `GetObject` | download audio to a temp file for fingerprinting; audio preview/playback (presigned); read `index/manifest.json` for catalog + dedup |
| `ListObjectsV2` | full-bucket explorer (`/files`, empty prefix); Catalog explorer (`catalog/` prefix); dashboard stats |
| `HeadObject` | object metadata / existence checks |
| `DeleteObject` | delete a track — **scoped to the `catalog/` prefix** (safety: `allowed_key_prefix` + delete confirmation) |
| Presigned `GetObject` | inline audio player + artifact downloads |

**Index nuance (document honestly in ARCHITECTURE.md):** MySQL is the *live queryable* index
(populated at ingest, what Dejavu matches against). **B2 holds the durable source of truth** —
raw audio, the portable SQL dump, and the manifest — from which MySQL can be re-seeded. The
"match against the B2-stored index" story = restore dump → MySQL → query. Represent both layers;
don't pretend Dejavu queries B2 directly.

**b2-native use:** none. Flag = none.

---

## 4. Key features (seed README + `docs/features/<feature>.md` stubs)

1. **Audio ingest & fingerprinting** (`docs/features/audio-ingest.md`) — upload WAV/MP3 → store to `catalog/` on B2 → Dejavu fingerprints locally → MySQL populated → manifest updated.
2. **Fingerprint index export** (`docs/features/fingerprint-index.md`) — dump the MySQL fingerprint DB (`index/fingerprints.sql`) + per-track JSON manifest (`index/manifest.json`, mapping B2 object key → track id / fingerprint count / canonical flag) back to B2.
3. **Deduplicate before ingest** (`docs/features/deduplicate.md`) — fingerprint a candidate, match against the index, flag duplicate B2 keys, log the result JSON to B2.
4. **Catalog / Library explorer** (`docs/features/catalog.md`) — app-scoped `catalog/` view with fingerprint status + inline audio playback.
5. **Bucket explorer + Upload** (keep starter `docs/features/file-browser.md`, adapt `file-upload.md`) — full-bucket browse + generic B2 upload.
6. **Dedup dashboard** (`docs/features/dashboard.md`, rewritten) — stat cards: *tracks in catalog*, *fingerprints indexed*, *duplicates detected (count + %)*, *total audio storage on B2*; a chart of ingests-over-time; a recent-ingests / recent-dedup-runs table. New aggregations flow `runtime → service → repo` and expose via TanStack Query hooks in `lib/queries.ts` (no bare `useEffect+fetch`).

### External API provider
**None.** Dejavu is a fully **on-device / local** capability — per `api-provider-selection.md`
Step 2 rule 1 (the sample's point is a local engine), LOCAL is the default; there is no remote
path and no provider key. Per feature:

| Feature | Provider/model | `deployment` | Est. cost / demo run | Key env var |
|---------|----------------|--------------|----------------------|-------------|
| Fingerprint + dedup | Dejavu (OSS, local) | **local** | $0 (no external API) | — (none) |

**CPU/GPU rule:** Dejavu computes spectrograms via NumPy/SciPy FFT — it is **CPU-only and has
no GPU code path**, so the "default to CPU" rule is satisfied inherently and CUDA→MPS→CPU
autodetect is **N/A** (no GPU backend exists to detect). Record this explicitly; do not add a
fake device-selection knob.

### Provider orchestration via Genblaze
**Not applicable** — the description does not mention Genblaze / `genblaze-*` / `genblaze-s3`.
Use plain `boto3` in `repo/`; no Genblaze SDK.

### Primary-entity lifecycle (UI completeness)
**Primary entity: `Track`** (an ingested audio recording in the catalog). All five lifecycle
verbs are exposed in the UI — **no omitted verbs** (`omitted_ui_verbs: []`):

| Verb | UI surface | Backend |
|------|-----------|---------|
| **create** (Ingest) | `/catalog` "Ingest track" form (file dropzone + fields) | `POST /catalog/ingest` (multipart) — store to `catalog/`, fingerprint, update manifest |
| **read** | `/catalog` list + `/catalog/{key}` detail (metadata, fingerprint count, matches, audio player) | `GET /catalog`, `GET /catalog/{key}` |
| **edit** | Edit-metadata form (pre-filled) on track detail — a metadata team edits canonical title/artist/notes and the canonical/duplicate label (audio bytes are immutable; metadata is not) | `PATCH /catalog/{key}` |
| **delete** | Delete button + `AlertDialog` confirm on the track row/detail | `DELETE /catalog/{key}` — remove B2 object (scoped to `catalog/`), drop its fingerprints from MySQL, update manifest |
| **run** (Deduplicate) | `/dedup` view — the marquee match workflow | `POST /dedup/match` (multipart candidate OR existing key) → result logged to `results/` |

> **CORS:** `main.py` currently allows `GET, POST, DELETE, OPTIONS`. **Add `PATCH`** to
> `allow_methods` for the edit verb.

### Form UX conventions (create/edit forms) — exemplar: `settings-form.tsx`
- **Ingest (create) form** fields:
  - `audio file` — dropzone (WAV/MP3), reuse upload validation.
  - `title` — free text (open-ended) — **create-form default hint** via `FormDescription`/placeholder: e.g. *"e.g. Artist – Track Name (used as the catalog display label)"*. Guidance only, never an autofill button.
  - `artist` — free text, optional, with placeholder hint.
  - `match sensitivity` — **finite value set → `Select`** (`Strict` / `Balanced` / `Loose`), maps to Dejavu's confidence threshold. Default `Balanced`, surfaced as the create-form default.
- **Edit form** opens pre-filled from the real Track (no default hints). `title`/`artist`/`notes` free text; `canonical status` (Canonical / Duplicate-of) uses a **selector** (finite set). Selector rule applies to both create and edit; default-hint rule only to create.

---

## 5. Doc transforms

| Starter doc | Action |
|-------------|--------|
| `README.md` | Rewrite: purpose, quickstart (add `docker compose -f infra/docker-compose.yml up -d mysql`, ffmpeg prereq for MP3 decode, B2 setup with **standard `B2_*` env vars**), feature list, commands. Repoint image refs to `docs/images/dejavu-audio-dedup-*.png` (filled later by sample-4). |
| `PRODUCT.md` | Rewrite for the audio-dedup product (users = ingest/metadata engineers; purpose; keep the "neutral, production-grade, WCAG AA" design principles). |
| `AGENTS.md` | Update repo map (add `repo/dejavu_index.py`, `infra/`, catalog/dedup services). Keep all layering invariants. **Add invariant: no `dejavu`/MySQL-driver import outside `repo/`.** |
| `ARCHITECTURE.md` | Update layout + data flows (ingest, export, dedup); document the MySQL-live-index vs B2-durable-index nuance. |
| `docs/features/metadata-extraction.md` | **Delete** (replaced by audio metadata inside `audio-ingest.md`). |
| `docs/features/file-upload.md` | Adapt → generic upload + note audio ingest lives in `audio-ingest.md`. |
| `docs/features/file-browser.md` | Keep (bucket explorer); add a Catalog cross-link. |
| `docs/features/dashboard.md` | Rewrite for dedup metrics. |
| `docs/features/audio-ingest.md`, `fingerprint-index.md`, `deduplicate.md`, `catalog.md` | **New** stubs (inputs/outputs/flow/edge cases), per `_template.md`. |
| `docs/SECURITY.md`, `docs/RELIABILITY.md`, `docs/dev-workflows.md`, `docs/app-workflows.md` | Light edits: audio-ingest/dedup journeys; note the `catalog/` delete scoping; MySQL dependency. |

---

## 6. Rename table (`vibe-coding-starter-kit` / `oss-starter-kit` → `dejavu-audio-dedup`)

| Identifier | From | To |
|-----------|------|----|
| kebab repo name | `vibe-coding-starter-kit` | `dejavu-audio-dedup` |
| pnpm workspace scope | `@vibe-coding-starter-kit/web` | `@dejavu-audio-dedup/web` (update `package.json` scripts, `apps/web/package.json` name) |
| root `package.json` name | `vibe-coding-starter-kit` | `dejavu-audio-dedup` |
| Title Case (`APP_NAME`) | `OSS Starter Kit` | `Dejavu Audio Dedup` |
| `APP_DESCRIPTION` | `File management dashboard powered by Backblaze B2` | `Audio fingerprint deduplication for large catalogs, on Backblaze B2` |
| FastAPI `title` (main.py) | `OSS Starter Kit API` | `Dejavu Audio Dedup API` |
| S3 `user_agent_extra` | `b2ai-oss-start` | `dejavu-audio-dedup` |
| UTM `utm_content` tag | `b2ai-oss-start` | `b2ai-dejavu-audio-dedup` |
| CI workflow name / slug | `vibe-coding-starter-kit` refs | `dejavu-audio-dedup` |
| Docker image/service tags | n/a (new) | `dejavu-audio-dedup-mysql` service in compose |

### Env-var standardization (parent CLAUDE.md Standard #3 — REQUIRED, this is a defect if skipped)
The starter deviates (`B2_KEY_ID`, `B2_ENDPOINT`, `b2_public_url`, no `B2_REGION`). Rename to the
standard set across `settings.py`, `main.py` (`REQUIRED_B2_SETTINGS`, placeholder check),
`b2_client.py`, `.env.example`, and all docs:

| Starter var | Standard var |
|-------------|--------------|
| `B2_KEY_ID` | `B2_APPLICATION_KEY_ID` |
| `B2_APPLICATION_KEY` | `B2_APPLICATION_KEY` (unchanged) |
| `B2_BUCKET_NAME` | `B2_BUCKET_NAME` (unchanged) |
| `B2_ENDPOINT` | derive from **`B2_REGION`** → `https://s3.<B2_REGION>.backblazeb2.com` (keep an optional `B2_ENDPOINT` override, but `B2_REGION` is the required, documented knob) |
| `b2_public_url` | `B2_PUBLIC_URL_BASE` |

Non-B2 infra vars (separate namespace, documented in `.env.example`): `FP_DB_HOST`,
`FP_DB_PORT`, `FP_DB_USER`, `FP_DB_PASSWORD`, `FP_DB_NAME` for the MySQL fingerprint DB.

---

## 7. Backend module plan (respect 300-line/file limit + layering)

- `repo/dejavu_index.py` — **only** dejavu + MySQL importer. `fingerprint_file(path, track_id)`, `recognize_file(path) → match|None`, `fingerprint_count()`, `drop_track(track_id)`, `dump_sql() → bytes`. Configures Dejavu from `FP_DB_*` settings.
- `repo/b2_client.py` / `b2_object.py` — keep; add small helpers `put_bytes(key, data, content_type)` / `put_json(key, obj)` for artifact writes (stay under 300 lines — split into `repo/b2_artifacts.py` if needed).
- `service/catalog.py` — ingest (B2 download → temp file → `dejavu_index.fingerprint_file` → manifest update via B2), list, detail, edit-metadata, delete (scoped).
- `service/dedup.py` — candidate → temp file → `recognize_file` → build `DedupResult` → log to `results/`.
- `service/index_export.py` — `dump_sql` + build manifest → B2 `index/`.
- `service/audio_metadata.py` — replaces image/PDF extraction; `mutagen`-based duration/samplerate/channels/bitrate.
- `types/` — `Track`, `TrackDetail`, `IngestResponse`, `DedupResult`, `CatalogStats` (Pydantic v2).
- `runtime/catalog.py`, `runtime/dedup.py` — routers (thin; no business logic).
- `tests/` — extend `test_structure.py` with a **dejavu-only-in-repo** assertion (symmetry with boto3 rule); add unit tests for manifest shaping + `DedupResult` mapping (no MySQL/network needed — mock the repo layer).

---

## 8. Dependencies & runtime risk (verify-watch — flag prominently)

- **Add** to `requirements.txt`: `dejavu` from a pinned installable source (`PyDejavu` is stale/py2 — prefer `git+https://github.com/worldveil/dejavu@<pinned-sha>`); its stack (`numpy` **pinned `<2`** — Dejavu is old, SciPy/NumPy2 ABI risk, mirrors other ML samples), `scipy`, `pydub`; MySQL driver (`PyMySQL` or `mysql-connector-python`, whichever the pinned Dejavu expects); `mutagen`. **Do NOT add `pyaudio`** — mic recognition is unused; file-only fingerprinting avoids the portaudio build pain.
- **Remove**: `Pillow`, `PyPDF2`.
- **System prereq (document, don't vendor):** `ffmpeg` for MP3 decode via pydub; WAV works without it.
- **⚠️ Native install risk (macOS arm64 / py3.11):** Dejavu is unmaintained and can be painful to install natively. If a fresh `pip install` proves unreliable during the later **verify** step, the sanctioned fallback is the **native-runtime container** pattern (cf. paddleocr/deoldify/paddlepaddle memories): run the Dejavu engine + MySQL in a `linux/arm64` container and have the FastAPI backend call it. **Leave this as a documented verify-watch in `docs/exec-plans/tech-debt-tracker.md` — do NOT force full containerization at build time**; the build step scaffolds + passes structural/lint review, it does not run the end-to-end ML pipeline.

---

## 9. Media-render & verify pre-emptions
- Track detail **and** catalog rows include a real `<audio>` element fed by a presigned URL, so
  media actually paints in both list and detail (pre-empts the verify media-render gate).
- Dedup result view renders the matched track with its player + confidence, not just JSON.

---

## Build checklist (Phase 2 must satisfy)
- [ ] Standard `B2_*` env vars everywhere; S3-only; custom UA `dejavu-audio-dedup`.
- [ ] Bucket explorer kept; Catalog (`catalog/`-scoped) explorer added.
- [ ] All 5 Track verbs in the UI; `PATCH` added to CORS.
- [ ] Ingest/edit forms follow selector + create-default-hint conventions.
- [ ] dejavu + MySQL driver confined to `repo/`; structural test enforces it.
- [ ] Pillow/PyPDF2 removed; audio deps added; numpy `<2`; no pyaudio.
- [ ] Docs rewritten per §5; README image refs repointed (no images created).
- [ ] `pnpm lint`, `pnpm build`, `pnpm lint:api`, `pnpm check:structure` clean.
