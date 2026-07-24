"""Index export: push the durable fingerprint index back to B2.

MySQL is the live index; B2 holds the portable copy. This dumps the MySQL
fingerprint tables to ``index/fingerprints.sql`` and re-writes the per-track
``index/manifest.json`` so the whole index can be re-seeded from B2.
"""

import logging

from app.repo import dejavu_index, put_bytes
from app.service import manifest as mf

logger = logging.getLogger(__name__)


def export_index() -> dict:
    """Dump the MySQL fingerprint DB + persist the manifest to B2.

    Returns a summary of what was written. Raises RuntimeError/EngineError-ish
    exceptions from the engine layer on MySQL failure (mapped to 502 upstream).
    """
    manifest = mf.load_manifest()
    # Re-persist the manifest so its `updated_at` reflects this export.
    mf.save_manifest(manifest)

    sql = dejavu_index.dump_sql()
    put_bytes(mf.SQL_DUMP_KEY, sql, content_type="application/sql")

    tracks = len(manifest.get("tracks", {}))
    return {
        "sql_dump_key": mf.SQL_DUMP_KEY,
        "manifest_key": mf.MANIFEST_KEY,
        "sql_dump_bytes": len(sql),
        "tracks": tracks,
        "fingerprints": dejavu_index.fingerprint_count(),
    }
