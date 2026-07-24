"""Dedup service: match a candidate against the live index and log the result.

The candidate is either an uploaded file or an existing catalog track. It is
fingerprinted in-memory and matched against MySQL; the verdict (is_duplicate,
matched track, confidence, time-offset) is returned and persisted to B2 under
``results/`` for an auditable ingest-decision log.
"""

import logging
import os
import tempfile
from datetime import UTC, datetime

from app.repo import dejavu_index, get_inline_url, get_object_bytes, put_json
from app.service import manifest as mf
from app.service.catalog import (
    INGEST_TYPES,
    EngineError,
    IngestError,
    _validate_catalog_key,
)
from app.service.upload import matches_content_signature, sanitize_filename
from app.types import DedupMatch, DedupResult

logger = logging.getLogger(__name__)

_EXT_SUFFIX = {"audio/mpeg": ".mp3", "audio/wav": ".wav"}


def _resolve_match(manifest: dict, raw: dict) -> DedupMatch:
    key = raw["track_name"] if raw["track_name"].startswith(mf.CATALOG_PREFIX) else None
    entry = mf.entry_for(manifest, key) if key else None
    return DedupMatch(
        track_id=raw.get("track_id"),
        track_name=raw["track_name"],
        key=key,
        title=(entry or {}).get("title"),
        confidence=raw["confidence"],
        offset_seconds=raw["offset_seconds"],
        hashes_matched=raw["hashes_matched"],
    )


def run_match(
    *,
    file_data: bytes | None = None,
    filename: str | None = None,
    content_type: str | None = None,
    existing_key: str | None = None,
    sensitivity: str = "balanced",
) -> DedupResult:
    from app.config import settings

    if existing_key:
        _validate_catalog_key(existing_key)
        file_data = get_object_bytes(existing_key)
        candidate_name = existing_key
        content_type = "audio/mpeg" if existing_key.lower().endswith(".mp3") else "audio/wav"
    else:
        if not file_data:
            raise IngestError("No candidate provided")
        if content_type not in INGEST_TYPES:
            raise IngestError(f"Unsupported audio type '{content_type}'", status_code=415)
        if not matches_content_signature(file_data, content_type):
            raise IngestError("File contents do not match the declared audio type", 415)
        candidate_name = sanitize_filename(filename or "candidate")

    threshold = settings.threshold_for(sensitivity)
    suffix = _EXT_SUFFIX.get(content_type or "", "")
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_data)
            tmp_path = tmp.name
        raw_matches = dejavu_index.recognize_matches(tmp_path, limit=5)
    except IngestError:
        raise
    except Exception as e:
        logger.warning("Recognize failed for %s", candidate_name, exc_info=True)
        raise EngineError(f"Recognition failed: {e}") from e
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # A candidate that is itself an existing catalog track will match itself —
    # exclude that self-match so dedup reports the *other* copy, if any.
    if existing_key:
        raw_matches = [m for m in raw_matches if m["track_name"] != existing_key]

    manifest = mf.load_manifest()
    matches = [_resolve_match(manifest, m) for m in raw_matches]
    top = matches[0] if matches else None
    is_dup = bool(top and top.confidence >= threshold)

    matched_key = top.key if (is_dup and top) else None
    matched_title = top.title if (is_dup and top) else None
    matched_audio_url = get_inline_url(matched_key) if matched_key else None

    created_at = datetime.now(UTC)
    result = DedupResult(
        candidate_name=candidate_name,
        candidate_key=existing_key,
        is_duplicate=is_dup,
        sensitivity=sensitivity,
        threshold=threshold,
        top_match=top,
        matches=matches,
        matched_key=matched_key,
        matched_title=matched_title,
        matched_audio_url=matched_audio_url,
        created_at=created_at,
    )

    result_key = f"{mf.RESULTS_PREFIX}dedup-{created_at.strftime('%Y%m%dT%H%M%S%f')}.json"
    try:
        put_json(result_key, result.model_dump(mode="json"))
        result.result_key = result_key
    except Exception:
        logger.warning("Failed to persist dedup result log", exc_info=True)

    return result
