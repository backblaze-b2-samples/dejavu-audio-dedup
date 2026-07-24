"""Unit tests for catalog Track shaping (repo boundary mocked)."""

from datetime import UTC, datetime

from app.service import catalog
from app.types import FileMetadata


def _obj(key: str) -> FileMetadata:
    return FileMetadata(
        key=key,
        filename=key.rsplit("/", 1)[-1],
        folder="catalog/",
        size_bytes=10,
        size_human="10 B",
        content_type="audio/wav",
        uploaded_at=datetime(2026, 1, 1, tzinfo=UTC),
        url=None,
    )


def test_list_tracks_marks_fingerprinted(monkeypatch):
    monkeypatch.setattr(catalog, "list_files", lambda prefix="": [_obj("catalog/a.wav")])
    monkeypatch.setattr(
        catalog.mf, "load_manifest",
        lambda: {"tracks": {"catalog/a.wav": {"track_id": 5, "fingerprint_count": 99, "title": "A"}}},
    )
    monkeypatch.setattr(catalog, "get_inline_url", lambda key, **k: "https://signed")

    tracks = catalog.list_tracks()
    assert tracks[0].fingerprint_status == "fingerprinted"
    assert tracks[0].fingerprint_count == 99
    assert tracks[0].title == "A"
    assert tracks[0].audio_url == "https://signed"


def test_list_tracks_marks_pending(monkeypatch):
    monkeypatch.setattr(catalog, "list_files", lambda prefix="": [_obj("catalog/b.wav")])
    monkeypatch.setattr(catalog.mf, "load_manifest", lambda: {"tracks": {}})
    monkeypatch.setattr(catalog, "get_inline_url", lambda key, **k: "https://signed")

    tracks = catalog.list_tracks()
    assert tracks[0].fingerprint_status == "pending"
    assert tracks[0].fingerprint_count == 0


def test_validate_catalog_key_rejects_outside_prefix():
    import pytest

    with pytest.raises(catalog.CatalogKeyError):
        catalog._validate_catalog_key("uploads/x.wav")
    with pytest.raises(catalog.CatalogKeyError):
        catalog._validate_catalog_key("catalog/../secret")
