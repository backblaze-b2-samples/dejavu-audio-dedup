"""Unit tests for DedupResult mapping. The engine + B2 boundary is mocked, so
these run with no MySQL, no network, and no dejavu install."""

import io
import wave

from app.repo import dejavu_index
from app.service import dedup


def _wav_bytes(seconds: float = 0.5, sample_rate: int = 8000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"\x00\x00" * int(seconds * sample_rate))
    return buf.getvalue()


def _raw(name, conf, offset=1.5, matched=100, tid=3):
    return {
        "track_id": tid,
        "track_name": name,
        "confidence": conf,
        "input_confidence": conf,
        "offset_seconds": offset,
        "hashes_matched": matched,
    }


def test_run_match_flags_duplicate(monkeypatch):
    monkeypatch.setattr(
        dejavu_index, "recognize_matches",
        lambda path, limit=5: [_raw("catalog/song.wav", 0.8)],
    )
    monkeypatch.setattr(dedup, "put_json", lambda *a, **k: None)
    monkeypatch.setattr(dedup, "get_inline_url", lambda key, **k: f"https://signed/{key}")
    monkeypatch.setattr(
        dedup.mf, "load_manifest",
        lambda: {"tracks": {"catalog/song.wav": {"title": "Song"}}},
    )

    result = dedup.run_match(
        file_data=_wav_bytes(), filename="cand.wav",
        content_type="audio/wav", sensitivity="balanced",
    )
    assert result.is_duplicate is True
    assert result.matched_key == "catalog/song.wav"
    assert result.matched_title == "Song"
    assert result.matched_audio_url == "https://signed/catalog/song.wav"
    assert result.top_match.confidence == 0.8
    assert result.matches[0].key == "catalog/song.wav"
    assert result.matches[0].offset_seconds == 1.5


def test_run_match_below_threshold_not_duplicate(monkeypatch):
    # A weak match under the balanced threshold (0.05) is reported but not a dup.
    monkeypatch.setattr(
        dejavu_index, "recognize_matches",
        lambda path, limit=5: [_raw("catalog/other.wav", 0.02)],
    )
    monkeypatch.setattr(dedup, "put_json", lambda *a, **k: None)
    monkeypatch.setattr(dedup, "get_inline_url", lambda key, **k: "x")
    monkeypatch.setattr(dedup.mf, "load_manifest", lambda: {"tracks": {}})

    result = dedup.run_match(
        file_data=_wav_bytes(), filename="cand.wav",
        content_type="audio/wav", sensitivity="balanced",
    )
    assert result.is_duplicate is False
    assert result.matched_key is None
    assert result.top_match is not None  # still surfaced as a weak match


def test_run_match_no_matches(monkeypatch):
    monkeypatch.setattr(dejavu_index, "recognize_matches", lambda path, limit=5: [])
    monkeypatch.setattr(dedup, "put_json", lambda *a, **k: None)
    monkeypatch.setattr(dedup.mf, "load_manifest", lambda: {"tracks": {}})

    result = dedup.run_match(
        file_data=_wav_bytes(), filename="cand.wav",
        content_type="audio/wav", sensitivity="strict",
    )
    assert result.is_duplicate is False
    assert result.top_match is None
    assert result.matches == []
