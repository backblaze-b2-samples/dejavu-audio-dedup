import logging

from fastapi import APIRouter, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.config import settings
from app.service.catalog import EngineError, IngestError
from app.service.dedup import run_match
from app.types import DedupResult

logger = logging.getLogger(__name__)

router = APIRouter()

_VALID_SENSITIVITY = {"strict", "balanced", "loose"}


@router.post("/dedup/match", response_model=DedupResult)
async def dedup_match_endpoint(
    request: Request,
    file: UploadFile | None = None,
    existing_key: str = Form(""),
    sensitivity: str = Form("balanced"),
):
    """Match a candidate against the live index. Provide EITHER an uploaded
    `file` (multipart) OR an `existing_key` naming a catalog track."""
    if sensitivity not in _VALID_SENSITIVITY:
        sensitivity = "balanced"

    file_data: bytes | None = None
    filename: str | None = None
    content_type: str | None = None
    if file is not None and file.filename:
        content_type = file.content_type or "application/octet-stream"
        filename = file.filename
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > settings.max_file_size:
                raise HTTPException(status_code=413, detail="File too large")
            chunks.append(chunk)
        file_data = b"".join(chunks)
    elif not existing_key:
        raise HTTPException(
            status_code=400, detail="Provide either a file or an existing_key"
        )

    try:
        result = await run_in_threadpool(
            run_match,
            file_data=file_data,
            filename=filename,
            content_type=content_type,
            existing_key=existing_key or None,
            sensitivity=sensitivity,
        )
    except IngestError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    except EngineError as e:
        raise HTTPException(status_code=502, detail=e.detail) from None
    logger.info(
        "Dedup run: candidate=%s duplicate=%s", result.candidate_name, result.is_duplicate
    )
    return result
