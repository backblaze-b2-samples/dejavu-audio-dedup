"""Audio-stream metadata extraction (replaces the starter's image/PDF path).

Uses `mutagen`, a pure-Python tag/stream reader — it reads the audio header
(duration, sample rate, channels, bitrate) without needing ffmpeg. Failures
are swallowed: a track that can't be probed still ingests and fingerprints;
the media fields simply stay null.
"""

import io
import logging

logger = logging.getLogger(__name__)


def _codec_from_content_type(content_type: str) -> str | None:
    return {
        "audio/mpeg": "mp3",
        "audio/wav": "wav",
        "video/mp4": "mp4",
    }.get(content_type)


def extract_audio_stream(file_data: bytes, content_type: str) -> dict:
    """Return ``{duration_seconds, sample_rate, channels, bitrate, codec}``
    for audio bytes. Missing values are omitted rather than set to null."""
    try:
        from mutagen import File as MutagenFile

        probe = MutagenFile(io.BytesIO(file_data))
        if probe is None or probe.info is None:
            return {}
        info = probe.info
        result: dict = {}
        codec = _codec_from_content_type(content_type)
        if codec:
            result["codec"] = codec
        length = getattr(info, "length", None)
        if length is not None:
            result["duration_seconds"] = round(float(length), 3)
        sample_rate = getattr(info, "sample_rate", None)
        if sample_rate:
            result["sample_rate"] = int(sample_rate)
        channels = getattr(info, "channels", None)
        if channels:
            result["channels"] = int(channels)
        bitrate = getattr(info, "bitrate", None)
        if bitrate:
            result["bitrate"] = int(bitrate)
        return result
    except Exception:
        logger.warning("Audio metadata extraction failed", exc_info=True)
        return {}
