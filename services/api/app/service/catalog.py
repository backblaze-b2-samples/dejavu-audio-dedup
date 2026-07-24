"""Catalog service: the Track lifecycle (ingest / read / edit / delete).

Ingest is the marquee write path: store audio to ``catalog/`` on B2, fingerprint
it locally with Dejavu into the live MySQL index, and record everything editable
in the B2 manifest. Reads join the ``catalog/`` object listing with the manifest.
Deletes are scoped to the ``catalog/`` prefix (safety) and also drop the track's
fingerprints from MySQL.
"""

import logging
import os
import tempfile
from datetime import UTC, datetime

from app.repo import (
    dejavu_index,
    delete_file,
    get_file_metadata,
    get_inline_url,
    list_files,
    upload_file,
)
from app.service import manifest as mf
from app.service.audio_metadata import extract_audio_stream
from app.service.upload import (
    matches_content_signature,
    sanitize_filename,
    validate_extension_matches_type,
)
from app.types import IngestResponse, Track, TrackDetail, TrackUpdate
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)

# Only real audio is ingestible into the catalog.
INGEST_TYPES = {"audio/mpeg", "audio/wav"}
_EXT_FOR_TYPE = {"audio/mpeg": ".mp3", "audio/wav": ".wav"}


class CatalogKeyError(Exception):
    def __init__(self, detail: str = "Invalid catalog key"):
        self.detail = detail
        super().__init__(detail)


class TrackNotFoundError(Exception):
    def __init__(self, detail: str = "Track not found"):
        self.detail = detail
        super().__init__(detail)


class IngestError(Exception):
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class EngineError(Exception):
    """Fingerprint engine / MySQL failure (surfaced as 502)."""

    def __init__(self, detail: str = "Fingerprint engine unavailable"):
        self.detail = detail
        super().__init__(detail)


def _validate_catalog_key(key: str) -> None:
    if not key or not key.startswith(mf.CATALOG_PREFIX):
        raise CatalogKeyError("Key must be under the catalog/ prefix")
    if any(bad in key for bad in ("../", "/..", "\\", "%2e", "\x00")):
        raise CatalogKeyError()


def _track_from(obj, entry: dict | None) -> Track:
    fingerprinted = bool(entry and entry.get("track_id") is not None)
    return Track(
        key=obj.key,
        filename=obj.filename,
        title=(entry or {}).get("title"),
        artist=(entry or {}).get("artist"),
        size_bytes=obj.size_bytes,
        size_human=obj.size_human,
        duration_seconds=(entry or {}).get("duration_seconds"),
        uploaded_at=obj.uploaded_at,
        fingerprint_status="fingerprinted" if fingerprinted else "pending",
        fingerprint_count=(entry or {}).get("fingerprint_count", 0),
        canonical_status=(entry or {}).get("canonical_status", "canonical"),
        audio_url=get_inline_url(obj.key, content_type=(entry or {}).get("codec_mime")),
    )


def list_tracks() -> list[Track]:
    """List catalog tracks (objects under ``catalog/``) joined with the manifest,
    newest-first."""
    manifest = mf.load_manifest()
    tracks = [
        _track_from(obj, mf.entry_for(manifest, obj.key))
        for obj in list_files(prefix=mf.CATALOG_PREFIX)
    ]
    tracks.sort(key=lambda t: t.uploaded_at, reverse=True)
    return tracks


def get_track(key: str) -> TrackDetail:
    _validate_catalog_key(key)
    obj = get_file_metadata(key)
    if not obj:
        raise TrackNotFoundError()
    entry = mf.entry_for(mf.load_manifest(), key) or {}
    return TrackDetail(
        key=key,
        filename=obj.filename,
        title=entry.get("title"),
        artist=entry.get("artist"),
        size_bytes=obj.size_bytes,
        size_human=obj.size_human,
        duration_seconds=entry.get("duration_seconds"),
        uploaded_at=obj.uploaded_at,
        fingerprint_status="fingerprinted" if entry.get("track_id") is not None else "pending",
        fingerprint_count=entry.get("fingerprint_count", 0),
        canonical_status=entry.get("canonical_status", "canonical"),
        audio_url=get_inline_url(key, content_type=obj.content_type),
        track_id=entry.get("track_id"),
        sample_rate=entry.get("sample_rate"),
        channels=entry.get("channels"),
        bitrate=entry.get("bitrate"),
        codec=entry.get("codec"),
        notes=entry.get("notes"),
        duplicate_of=entry.get("duplicate_of"),
        sensitivity=entry.get("sensitivity", "balanced"),
    )


def ingest_track(
    file_data: bytes,
    filename: str,
    title: str | None,
    artist: str | None,
    sensitivity: str,
    content_type: str,
) -> IngestResponse:
    """Store → fingerprint → manifest. Also runs a dedup check against the
    existing index *before* adding the new fingerprints, so a re-upload is
    flagged (and labelled canonical/duplicate)."""
    from app.config import settings

    if content_type not in INGEST_TYPES:
        raise IngestError(f"Unsupported audio type '{content_type}'", status_code=415)
    if not file_data:
        raise IngestError("Empty file")
    safe_name = sanitize_filename(filename)
    if not validate_extension_matches_type(safe_name, content_type):
        raise IngestError("File extension does not match audio type", status_code=415)
    if not matches_content_signature(file_data, content_type):
        raise IngestError("File contents do not match the declared audio type", status_code=415)

    key = f"{mf.CATALOG_PREFIX}{safe_name}"
    upload_file(file_data, key, content_type)
    stream = extract_audio_stream(file_data, content_type)

    threshold = settings.threshold_for(sensitivity)
    suffix = _EXT_FOR_TYPE.get(content_type, "")
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_data)
            tmp_path = tmp.name
        # Dedup BEFORE adding our own hashes so we can't match ourselves.
        pre = dejavu_index.recognize_file(tmp_path)
        is_dup = bool(pre and pre["confidence"] >= threshold and pre["track_name"] != key)
        fp = dejavu_index.fingerprint_file(tmp_path, track_name=key)
    except (IngestError, CatalogKeyError):
        raise
    except Exception as e:  # dejavu / MySQL / pydub failure
        logger.warning("Fingerprint failed for %s", key, exc_info=True)
        raise EngineError(f"Fingerprinting failed: {e}") from e
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    matched_key = pre["track_name"] if is_dup else None
    manifest = mf.load_manifest()
    matched_title = None
    if matched_key:
        matched_title = (mf.entry_for(manifest, matched_key) or {}).get("title")
    mf.upsert_entry(manifest, key, {
        "track_id": fp["track_id"],
        "fingerprint_count": fp["fingerprint_count"],
        "title": title or safe_name,
        "artist": artist,
        "sensitivity": sensitivity,
        "canonical_status": "duplicate" if is_dup else "canonical",
        "duplicate_of": matched_key,
        "size_bytes": len(file_data),
        "ingested_at": datetime.now(UTC).isoformat(),
        **stream,
    })
    mf.save_manifest(manifest)

    msg = (
        f"Duplicate of {matched_key}" if is_dup
        else f"Ingested and fingerprinted ({fp['fingerprint_count']} hashes)"
    )
    return IngestResponse(
        key=key,
        track_id=fp["track_id"],
        fingerprint_count=fp["fingerprint_count"],
        duration_seconds=stream.get("duration_seconds"),
        is_duplicate=is_dup,
        matched_key=matched_key,
        matched_title=matched_title,
        confidence=pre["confidence"] if pre else None,
        message=msg,
    )


def edit_track(key: str, update: TrackUpdate) -> TrackDetail:
    _validate_catalog_key(key)
    if not get_file_metadata(key):
        raise TrackNotFoundError()
    manifest = mf.load_manifest()
    fields = update.model_dump(exclude_none=True)
    mf.upsert_entry(manifest, key, fields)
    mf.save_manifest(manifest)
    return get_track(key)


def delete_track(key: str) -> None:
    """Delete a catalog track: remove the B2 object (scoped to catalog/), drop
    its fingerprints from MySQL, and remove its manifest entry."""
    _validate_catalog_key(key)
    manifest = mf.load_manifest()
    entry = mf.entry_for(manifest, key)
    delete_file(key)
    track_id = (entry or {}).get("track_id")
    if track_id is not None:
        try:
            dejavu_index.drop_track(int(track_id))
        except Exception:
            logger.warning("Failed to drop fingerprints for %s", key, exc_info=True)
    mf.remove_entry(manifest, key)
    mf.save_manifest(manifest)


def get_catalog_stats():
    """Aggregate dedup dashboard metrics from the manifest + live index."""
    from app.types import CatalogStats

    manifest = mf.load_manifest()
    entries = manifest.get("tracks", {})
    total = len(entries)
    duplicates = sum(1 for e in entries.values() if e.get("canonical_status") == "duplicate")
    total_bytes = sum(int(e.get("size_bytes", 0)) for e in entries.values())
    try:
        indexed = dejavu_index.fingerprint_count()
    except Exception:
        indexed = sum(int(e.get("fingerprint_count", 0)) for e in entries.values())
    pct = round((duplicates / total) * 100, 1) if total else 0.0
    return CatalogStats(
        tracks_in_catalog=total,
        fingerprints_indexed=indexed,
        duplicates_detected=duplicates,
        duplicate_pct=pct,
        total_audio_bytes=total_bytes,
        total_audio_human=humanize_bytes(total_bytes),
    )


def get_ingest_activity(days: int = 7):
    """Daily ingest counts for the last N days, from manifest ingested_at."""
    from collections import defaultdict
    from datetime import timedelta

    from app.types import DailyIngestCount

    manifest = mf.load_manifest()
    today = datetime.now(UTC).date()
    cutoff = today - timedelta(days=days - 1)
    counts: dict[str, int] = defaultdict(int)
    for e in manifest.get("tracks", {}).values():
        ts = e.get("ingested_at")
        if not ts:
            continue
        try:
            d = datetime.fromisoformat(ts).date()
        except ValueError:
            continue
        if d >= cutoff:
            counts[d.isoformat()] += 1
    return [
        DailyIngestCount(
            date=(cutoff + timedelta(days=i)).isoformat(),
            ingests=counts.get((cutoff + timedelta(days=i)).isoformat(), 0),
        )
        for i in range(days)
    ]
