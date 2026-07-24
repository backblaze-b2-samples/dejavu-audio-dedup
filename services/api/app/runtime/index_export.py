import logging

from fastapi import APIRouter, HTTPException

from app.service.catalog import EngineError
from app.service.index_export import export_index

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/index/export")
def export_index_endpoint():
    """Dump the MySQL fingerprint index + manifest to B2 (`index/`)."""
    try:
        summary = export_index()
    except EngineError as e:
        raise HTTPException(status_code=502, detail=e.detail) from None
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from None
    logger.info("Index exported: %s", summary.get("sql_dump_key"))
    return summary
