import hashlib
import logging
from datetime import UTC, datetime

from app.service.audio_metadata import extract_audio_stream
from app.types import FileMetadataDetail
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)


def extract_metadata(
    file_data: bytes,
    filename: str,
    content_type: str,
    uploaded_at: datetime | None = None,
) -> FileMetadataDetail:
    """Compute rich metadata from raw file bytes.

    For this app the interesting derived fields are audio-stream properties
    (duration, sample rate, channels, bitrate) — extracted for `audio/*`
    content types via `service.audio_metadata`. Checksums are always computed.

    `uploaded_at` is the object's real upload time; callers recomputing metadata
    for an already-stored object MUST pass it (from head_object's LastModified)
    so the panel shows the true upload time rather than the recompute time. It
    defaults to now only for the fresh-upload path, where the two coincide.
    """
    md5 = hashlib.md5(file_data, usedforsecurity=False).hexdigest()
    sha256 = hashlib.sha256(file_data).hexdigest()
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    extra: dict = {}
    if content_type.startswith("audio/") or content_type == "video/mp4":
        extra = extract_audio_stream(file_data, content_type)

    return FileMetadataDetail(
        filename=filename,
        size_bytes=len(file_data),
        size_human=humanize_bytes(len(file_data)),
        mime_type=content_type,
        extension=extension,
        md5=md5,
        sha256=sha256,
        uploaded_at=uploaded_at if uploaded_at is not None else datetime.now(UTC),
        **extra,
    )
