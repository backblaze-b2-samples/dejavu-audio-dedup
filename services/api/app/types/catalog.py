from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Sensitivity = Literal["strict", "balanced", "loose"]
CanonicalStatus = Literal["canonical", "duplicate"]
FingerprintStatus = Literal["fingerprinted", "pending"]


class Track(BaseModel):
    """A catalog audio recording (list view)."""

    key: str  # catalog/<filename>
    filename: str
    title: str | None = None
    artist: str | None = None
    size_bytes: int
    size_human: str
    duration_seconds: float | None = None
    uploaded_at: datetime
    fingerprint_status: FingerprintStatus
    fingerprint_count: int = 0
    canonical_status: CanonicalStatus = "canonical"
    audio_url: str | None = None  # presigned URL for inline playback


class TrackDetail(Track):
    """A single track with its full manifest + audio-stream metadata."""

    track_id: int | None = None
    sample_rate: int | None = None
    channels: int | None = None
    bitrate: int | None = None
    codec: str | None = None
    notes: str | None = None
    duplicate_of: str | None = None
    sensitivity: Sensitivity = "balanced"
    md5: str | None = None


class TrackUpdate(BaseModel):
    """Editable metadata for a track (audio bytes are immutable)."""

    title: str | None = None
    artist: str | None = None
    notes: str | None = None
    canonical_status: CanonicalStatus | None = None
    duplicate_of: str | None = None


class IngestResponse(BaseModel):
    key: str
    track_id: int | None = None
    fingerprint_count: int
    duration_seconds: float | None = None
    is_duplicate: bool
    matched_key: str | None = None
    matched_title: str | None = None
    confidence: float | None = None
    message: str


class CatalogStats(BaseModel):
    tracks_in_catalog: int
    fingerprints_indexed: int
    duplicates_detected: int
    duplicate_pct: float
    total_audio_bytes: int
    total_audio_human: str


class DailyIngestCount(BaseModel):
    date: str
    ingests: int
