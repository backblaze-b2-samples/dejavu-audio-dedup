<!-- last_verified: 2026-03-10 -->
# App Workflows

User journeys inside the application.

## Ingest a Track

- User navigates to `/catalog` and clicks **Ingest track**
- Chooses a WAV/MP3, sets a title/artist, and picks a **match sensitivity** (Strict/Balanced/Loose)
- API stores the audio at `catalog/<name>` on B2, fingerprints it locally into MySQL, and updates the manifest on B2
- The ingest also checks the candidate against the existing index — a match is flagged as a duplicate
- On success: toast; the catalog list and dashboard refresh
- See: [Audio Ingest & Fingerprinting](features/audio-ingest.md)

## Deduplicate Before Ingest

- User navigates to `/dedup`
- Picks a candidate source: upload a file, or select an existing catalog track
- Chooses a sensitivity and clicks **Run dedup**
- API fingerprints the candidate and matches it against the live index
- Result panel shows the verdict (Duplicate / No duplicate), the matched track with an inline player, confidence and time-offset, and all matches
- The verdict is logged to `results/` on B2
- See: [Deduplicate Before Ingest](features/deduplicate.md)

## Browse & Manage the Catalog

- User navigates to `/catalog` → list of ingested tracks with fingerprint status and inline players
- Opens a track's **Details** → metadata, player, and a pre-filled edit form (title/artist/notes + canonical-status selector)
- Deletes a track → confirm dialog → object removed from B2 (scoped to `catalog/`), fingerprints dropped from MySQL, manifest updated
- See: [Catalog Explorer](features/catalog.md)

## Upload Files

- User navigates to `/upload`
- Drops or selects files in the dropzone
- Client validates file size (max 100MB) and type
- Progress bar shows per-file upload status
- On success: toast notification, green checkmark
- On failure: red status icon with error message
- User can clear completed uploads
- See: [File Upload](features/file-upload.md)

## Browse and Manage Files

- User navigates to `/files`
- Page loads file list from API (sorted most recent first)
- Files displayed in tree view with folders and type-specific icons
- Top-level folders auto-expand on load
- Hover a file row to see action buttons (preview / download / delete)
- **Preview**: opens dialog with image/PDF preview + metadata panel
- **Download**: fetches presigned URL, browser downloads file
- **Delete**: removes file from B2, row removed from tree, toast confirms
- Empty bucket shows "No files found" with upload prompt
- See: [File Browser](features/file-browser.md)

## View Dashboard

- User navigates to `/` (home)
- Three parallel API calls load: stats, recent files, upload activity
- Stats cards show: total files, storage used, uploads today, total downloads
- Upload chart shows last 7 days of upload activity as bar chart
- Recent uploads table shows last 10 files with filename, size, type, date
- Empty state: "No files uploaded yet" messages
- See: [Dashboard](features/dashboard.md)
