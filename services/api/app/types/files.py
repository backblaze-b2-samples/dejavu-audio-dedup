from datetime import datetime

from pydantic import BaseModel


class FileMetadata(BaseModel):
    key: str
    filename: str
    folder: str
    size_bytes: int
    size_human: str
    content_type: str
    uploaded_at: datetime
    url: str | None = None


class FileMetadataDetail(BaseModel):
    filename: str
    size_bytes: int
    size_human: str
    mime_type: str
    extension: str
    md5: str
    sha256: str
    uploaded_at: datetime
    # Audio stream properties (populated for audio/* uploads via mutagen)
    duration_seconds: float | None = None
    sample_rate: int | None = None
    channels: int | None = None
    bitrate: int | None = None
    codec: str | None = None
