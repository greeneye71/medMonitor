"""Archive endpoints."""
import logging
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/archive", tags=["archive"])


@router.get("/status")
async def archive_status():
    try:
        from backend.services.archive_service import ArchiveService
        from backend.services.config_service import config_service
        from backend.dependencies import get_db
        svc = ArchiveService(db=get_db(), config_service=config_service)
        return svc.get_status()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("archive_status failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run")
async def archive_run():
    try:
        from backend.services.archive_service import ArchiveService
        from backend.services.config_service import config_service
        from backend.dependencies import get_db
        svc = ArchiveService(db=get_db(), config_service=config_service)
        return await svc.run()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("archive_run failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
