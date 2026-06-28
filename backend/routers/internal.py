from fastapi import APIRouter
from pydantic import BaseModel

from core.logger import logger
from ws_manager import manager

router = APIRouter()


class CaseUpdatedRequest(BaseModel):
    case_id: str
    status: str
    title: str | None = None
    summary: str | None = None


@router.get("/")
@router.get("/health")
def read_root():
    logger.info("Health check endpoint called")
    return {"message": "Lawyer Dashboard Gateway is running"}


@router.post("/internal/case-updated")
async def case_updated(request: CaseUpdatedRequest):
    logger.info(f"Case {request.case_id} status updated to {request.status}, broadcasting")
    msg: dict = {
        "type": "CASE_STATUS_UPDATED",
        "case_id": request.case_id,
        "status": request.status,
    }
    if request.title is not None:
        msg["title"] = request.title
    if request.summary is not None:
        msg["summary"] = request.summary
    await manager.broadcast_dashboard(msg)
    return {"ok": True}
