"""Log streaming endpoint."""

from fastapi import APIRouter, Query, Request

router = APIRouter(prefix="/api", tags=["logs"])


@router.get("/logs")
async def get_logs(
    request: Request,
    level: str = Query("ALL", pattern="^(ALL|INFO|WARNING|ERROR)$"),
    limit: int = Query(200, ge=1, le=1000),
):
    collector = getattr(request.app.state, "log_collector", None)
    if collector is None:
        return []
    return collector.get_entries(level=level, limit=limit)
