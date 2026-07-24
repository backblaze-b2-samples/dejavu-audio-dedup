"""Unit tests for manifest shaping (no B2/MySQL — pure dict logic)."""

from app.service import manifest as mf


def test_upsert_creates_and_skips_none():
    m = {"version": 1, "tracks": {}}
    mf.upsert_entry(
        m, "catalog/a.wav", {"title": "A", "track_id": 1, "artist": None}
    )
    entry = mf.entry_for(m, "catalog/a.wav")
    assert entry["title"] == "A"
    assert entry["track_id"] == 1
    # None values are not written (they'd clobber existing data on re-upsert).
    assert "artist" not in entry


def test_upsert_merges_without_clobbering():
    m = {"version": 1, "tracks": {}}
    mf.upsert_entry(m, "catalog/a.wav", {"title": "A", "track_id": 1})
    mf.upsert_entry(m, "catalog/a.wav", {"artist": "X"})
    entry = mf.entry_for(m, "catalog/a.wav")
    assert entry["title"] == "A"  # preserved
    assert entry["artist"] == "X"  # added


def test_remove_entry():
    m = {"version": 1, "tracks": {"catalog/a.wav": {"title": "A"}}}
    removed = mf.remove_entry(m, "catalog/a.wav")
    assert removed["title"] == "A"
    assert mf.entry_for(m, "catalog/a.wav") is None


def test_entry_for_missing_returns_none():
    assert mf.entry_for({"tracks": {}}, "catalog/none.wav") is None
