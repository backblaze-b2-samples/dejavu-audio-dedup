"""The per-track manifest — B2 is the metadata source of truth.

Catalog objects under ``catalog/`` hold immutable audio bytes only. Everything
editable about a track (title, artist, notes, canonical/duplicate label,
fingerprint id/count, sensitivity, extracted stream properties) lives in a
single JSON manifest at ``index/manifest.json`` on B2. This module owns its
shape; it reads/writes through the repo layer (``get_json`` / ``put_json``).
"""

from datetime import UTC, datetime

from app.repo import get_json, put_json

CATALOG_PREFIX = "catalog/"
MANIFEST_KEY = "index/manifest.json"
SQL_DUMP_KEY = "index/fingerprints.sql"
RESULTS_PREFIX = "results/"

MANIFEST_VERSION = 1


def load_manifest() -> dict:
    """Load the manifest from B2, or an empty one if it doesn't exist yet."""
    data = get_json(MANIFEST_KEY)
    if not isinstance(data, dict) or "tracks" not in data:
        return {"version": MANIFEST_VERSION, "updated_at": None, "tracks": {}}
    return data


def save_manifest(manifest: dict) -> None:
    manifest["version"] = MANIFEST_VERSION
    manifest["updated_at"] = datetime.now(UTC).isoformat()
    put_json(MANIFEST_KEY, manifest)


def entry_for(manifest: dict, key: str) -> dict | None:
    return manifest.get("tracks", {}).get(key)


def upsert_entry(manifest: dict, key: str, fields: dict) -> dict:
    """Merge `fields` into the manifest entry for `key`, creating it if new."""
    tracks = manifest.setdefault("tracks", {})
    entry = tracks.get(key, {})
    entry.update({k: v for k, v in fields.items() if v is not None})
    tracks[key] = entry
    return entry


def remove_entry(manifest: dict, key: str) -> dict | None:
    return manifest.get("tracks", {}).pop(key, None)
