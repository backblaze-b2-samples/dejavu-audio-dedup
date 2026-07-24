import logging

from fastapi import APIRouter, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.config import settings
from app.service.catalog import (
    CatalogKeyError,
    EngineError,
    IngestError,
    TrackNotFoundError,
    delete_track,
    edit_track,
    get_catalog_stats,
    get_ingest_activity,
    get_track,
    ingest_track,
    list_tracks,
)
from app.types import (
    CatalogStats,
    DailyIngestCount,
    IngestResponse,
    Track,
    TrackDetail,
    TrackUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_VALID_SENSITIVITY = {"strict", "balanced", "loose"}


def _map_key_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, CatalogKeyError):
        return HTTPException(status_code=400, detail=exc.detail)
    if isinstance(exc, TrackNotFoundError):
        return HTTPException(status_code=404, detail=exc.detail)
    if isinstance(exc, EngineError):
        return HTTPException(status_code=502, detail=exc.detail)
    return HTTPException(status_code=500, detail="Catalog operation failed")


@router.get("/catalog", response_model=list[Track])
def list_catalog_endpoint():
    return list_tracks()


@router.get("/catalog/stats", response_model=CatalogStats)
def catalog_stats_endpoint():
    return get_catalog_stats()


@router.get("/catalog/stats/activity", response_model=list[DailyIngestCount])
def catalog_activity_endpoint(days: int = 7):
    if days < 1 or days > 90:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 90")
    return get_ingest_activity(days=days)


@router.post("/catalog/ingest", response_model=IngestResponse)
async def ingest_endpoint(
    request: Request,
    file: UploadFile,
    title: str = Form(""),
    artist: str = Form(""),
    sensitivity: str = Form("balanced"),
):
    content_type = file.content_type or "application/octet-stream"
    if sensitivity not in _VALID_SENSITIVITY:
        sensitivity = "balanced"

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

    try:
        result = await run_in_threadpool(
            ingest_track,
            file_data=file_data,
            filename=file.filename or "",
            title=title or None,
            artist=artist or None,
            sensitivity=sensitivity,
            content_type=content_type,
        )
    except IngestError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    except EngineError as e:
        raise HTTPException(status_code=502, detail=e.detail) from None
    logger.info("Track ingested: key=%s duplicate=%s", result.key, result.is_duplicate)
    return result


@router.get("/catalog-item", response_model=TrackDetail)
def get_track_endpoint(key: str):
    try:
        return get_track(key)
    except (CatalogKeyError, TrackNotFoundError) as e:
        raise _map_key_errors(e) from None


@router.patch("/catalog-item", response_model=TrackDetail)
def edit_track_endpoint(key: str, update: TrackUpdate):
    try:
        return edit_track(key, update)
    except (CatalogKeyError, TrackNotFoundError) as e:
        raise _map_key_errors(e) from None


@router.delete("/catalog-item")
def delete_track_endpoint(key: str):
    try:
        delete_track(key)
    except CatalogKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Failed to delete track") from None
    logger.info("Track deleted: key=%s", key)
    return {"deleted": True, "key": key}
