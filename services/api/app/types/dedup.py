from datetime import datetime

from pydantic import BaseModel


class DedupMatch(BaseModel):
    track_id: int | None = None
    track_name: str
    key: str | None = None  # resolved catalog key, if the match maps to one
    title: str | None = None
    confidence: float
    offset_seconds: float
    hashes_matched: int


class DedupResult(BaseModel):
    candidate_name: str
    candidate_key: str | None = None  # set when the candidate was an existing catalog track
    is_duplicate: bool
    sensitivity: str
    threshold: float
    top_match: DedupMatch | None = None
    matches: list[DedupMatch] = []
    matched_key: str | None = None
    matched_title: str | None = None
    matched_audio_url: str | None = None  # presigned URL to play the matched track
    created_at: datetime
    result_key: str | None = None  # B2 key of the persisted result log
