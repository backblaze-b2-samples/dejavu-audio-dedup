"""Dejavu acoustic-fingerprint engine + MySQL fingerprint store.

This is the ONLY module that imports `dejavu` or the MySQL driver — the
symmetric counterpart to the boto3-only-in-repo rule, both enforced by
`tests/test_structure.py`. Every heavy/native import is done lazily *inside*
the functions so the rest of the app (and the whole test suite) imports fine
without the audio stack installed; the imports fire only on a real call.

Index model (see ARCHITECTURE.md): MySQL is the LIVE, queryable index Dejavu
matches against. Backblaze B2 holds the durable source of truth — the raw
audio, the portable SQL dump, and the manifest — from which MySQL can be
re-seeded. Dejavu never talks to B2 directly.
"""

import datetime as _dt
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Dejavu's canonical MySQL schema (table names it creates + queries).
_SONGS_TABLE = "songs"
_FINGERPRINTS_TABLE = "fingerprints"


def _dejavu_config() -> dict:
    return {"database": settings.fp_db_config, "database_type": "mysql"}


def _get_djv():
    """Build a Dejavu handle. Its constructor runs `db.setup()`, creating the
    `songs`/`fingerprints` tables on first use."""
    from dejavu import Dejavu

    return Dejavu(_dejavu_config())


def _mysql_conn():
    """Direct MySQL connection for the repo's own queries (id lookup, counts,
    delete, dump). Uses the same driver Dejavu imports."""
    import mysql.connector

    return mysql.connector.connect(**settings.fp_db_config)


def _song_row(track_name: str) -> tuple[int, int] | None:
    """Return (song_id, total_hashes) for the most recently created song with
    this name, or None. Uses Dejavu's `songs.total_hashes` count column."""
    conn = _mysql_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            f"SELECT song_id, total_hashes FROM {_SONGS_TABLE} "
            "WHERE song_name = %s ORDER BY date_created DESC LIMIT 1",
            (track_name,),
        )
        row = cur.fetchone()
        cur.close()
        return (int(row[0]), int(row[1] or 0)) if row else None
    finally:
        conn.close()


def fingerprint_file(path: str, track_name: str) -> dict:
    """Fingerprint an audio file into the live MySQL index.

    Returns ``{"track_id": int | None, "fingerprint_count": int}``. Dejavu
    decodes the audio (WAV natively; MP3 via pydub+ffmpeg), computes
    spectrogram-peak hashes, and inserts them under ``track_name``.
    """
    djv = _get_djv()
    djv.fingerprint_file(path, song_name=track_name)
    row = _song_row(track_name)
    if row is None:
        return {"track_id": None, "fingerprint_count": 0}
    return {"track_id": row[0], "fingerprint_count": row[1]}


def _shape_match(match: dict) -> dict:
    """Normalize one Dejavu result dict into plain JSON-friendly fields."""
    name = match.get("song_name")
    if isinstance(name, (bytes, bytearray)):
        name = name.decode("utf-8", errors="replace")
    return {
        "track_id": int(match["song_id"]) if match.get("song_id") is not None else None,
        "track_name": name or "",
        "confidence": float(match.get("fingerprinted_confidence") or 0.0),
        "input_confidence": float(match.get("input_confidence") or 0.0),
        "offset_seconds": float(match.get("offset_seconds") or 0.0),
        "hashes_matched": int(match.get("hashes_matched_in_input") or 0),
    }


def recognize_file(path: str) -> dict | None:
    """Match a candidate audio file against the live index.

    Returns the best match (shaped by ``_shape_match``) or ``None`` when Dejavu
    finds nothing. Confidence is Dejavu's ``fingerprinted_confidence`` in [0, 1].
    """
    from dejavu.logic.recognizer.file_recognizer import FileRecognizer

    djv = _get_djv()
    result = djv.recognize(FileRecognizer, path)
    matches = (result or {}).get("results") or []
    if not matches:
        return None
    return _shape_match(matches[0])


def recognize_matches(path: str, limit: int = 5) -> list[dict]:
    """Return up to ``limit`` matches for a candidate, best-first."""
    from dejavu.logic.recognizer.file_recognizer import FileRecognizer

    djv = _get_djv()
    result = djv.recognize(FileRecognizer, path)
    matches = (result or {}).get("results") or []
    return [_shape_match(m) for m in matches[:limit]]


def _scalar(query: str) -> int:
    conn = _mysql_conn()
    try:
        cur = conn.cursor()
        try:
            cur.execute(query)
            row = cur.fetchone()
            return int(row[0]) if row and row[0] is not None else 0
        except Exception:
            # Tables not created yet (no fingerprints ingested) → zero.
            return 0
        finally:
            cur.close()
    finally:
        conn.close()


def fingerprint_count() -> int:
    """Total number of fingerprint hashes across the whole index."""
    return _scalar(f"SELECT COUNT(*) FROM {_FINGERPRINTS_TABLE}")


def song_count() -> int:
    """Number of distinct fingerprinted tracks in the live index."""
    return _scalar(f"SELECT COUNT(*) FROM {_SONGS_TABLE}")


def drop_track(track_id: int) -> None:
    """Remove a track's fingerprints from the live index (delete path)."""
    conn = _mysql_conn()
    try:
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {_FINGERPRINTS_TABLE} WHERE song_id = %s", (track_id,))
        cur.execute(f"DELETE FROM {_SONGS_TABLE} WHERE song_id = %s", (track_id,))
        conn.commit()
        cur.close()
    finally:
        conn.close()


def _sql_literal(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (bytes, bytearray)):
        return "0x" + value.hex() if value else "''"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (_dt.datetime, _dt.date)):
        return "'" + value.isoformat(sep=" ") + "'"
    return "'" + str(value).replace("\\", "\\\\").replace("'", "''") + "'"


def dump_sql() -> bytes:
    """Serialize the live MySQL fingerprint index to a portable SQL dump.

    Emits the exact DDL (`SHOW CREATE TABLE`) plus INSERT statements for both
    Dejavu tables, so the dump can re-seed a fresh MySQL from B2. Returns a
    header-only dump when the tables don't exist yet (nothing fingerprinted).
    """
    header = [
        "-- Dejavu fingerprint index dump",
        f"-- generated_at: {_dt.datetime.now(_dt.UTC).isoformat()}",
        "SET FOREIGN_KEY_CHECKS=0;",
    ]
    conn = _mysql_conn()
    try:
        cur = conn.cursor()
        out = list(header)
        for table in (_SONGS_TABLE, _FINGERPRINTS_TABLE):
            try:
                cur.execute(f"SHOW CREATE TABLE {table}")
                ddl = cur.fetchone()[1]
            except Exception:
                out.append(f"-- table `{table}` not present (no fingerprints yet)")
                continue
            out.append(f"\nDROP TABLE IF EXISTS `{table}`;")
            out.append(ddl + ";")
            cur.execute(f"SELECT * FROM {table}")
            cols = [d[0] for d in cur.description]
            collist = "`,`".join(cols)
            for row in cur.fetchall():
                vals = ", ".join(_sql_literal(v) for v in row)
                out.append(f"INSERT INTO `{table}` (`{collist}`) VALUES ({vals});")
        out.append("SET FOREIGN_KEY_CHECKS=1;")
        cur.close()
        return ("\n".join(out) + "\n").encode("utf-8")
    finally:
        conn.close()
