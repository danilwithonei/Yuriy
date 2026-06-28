from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_lawyer
from core.logger import logger
from routers.deps import intake, lawyer, verify_ownership
from ws_manager import manager

router = APIRouter()


class CreateCaseRequest(BaseModel):
    type: str = "direct"


class PinCaseRequest(BaseModel):
    pinned: bool


class DeleteCaseResponse(BaseModel):
    case_id: str
    deleted: bool


@router.post("/cases")
async def create_case(request: CreateCaseRequest, lawyer_id: int = Depends(get_current_lawyer)):
    logger.info(f"Create case request: type={request.type}")
    try:
        return await intake.create_case(request.type, "frontend", lawyer_id)
    except Exception as e:
        logger.error(f"Error creating case: {e}")
        raise HTTPException(status_code=502, detail="Intake Service unavailable")


@router.get("/cases")
async def list_cases(lawyer_id: int = Depends(get_current_lawyer)):
    logger.info(f"Listing cases for lawyer_id={lawyer_id}")
    try:
        return await intake.list_cases(lawyer_id)
    except Exception as e:
        logger.error(f"Error fetching cases from Intake Service: {e}")
        raise HTTPException(status_code=502, detail="Intake Service Error")


@router.get("/cases/{case_id}")
async def get_case(case_id: str, lawyer_id: int = Depends(get_current_lawyer)):
    logger.info(f"Fetching details for case_id={case_id}")
    intake_data = await verify_ownership(case_id, lawyer_id)
    try:
        lawyer_messages = await lawyer.get_messages(case_id)
    except Exception as e:
        logger.warning(f"Could not fetch lawyer messages for case {case_id}: {e}")
        lawyer_messages = []
    return {"case": intake_data["case"], "messages": intake_data["messages"] + lawyer_messages}


@router.patch("/cases/{case_id}/pin")
async def pin_case(case_id: str, request: PinCaseRequest, lawyer_id: int = Depends(get_current_lawyer)):
    await verify_ownership(case_id, lawyer_id)
    logger.info(f"Pin case {case_id} -> pinned={request.pinned}")
    try:
        await intake.pin(case_id, request.pinned)
        await lawyer.pin(case_id, request.pinned)
    except Exception as e:
        logger.error(f"Error pinning case {case_id}: {e}")
        raise HTTPException(status_code=502, detail="Service unavailable")
    await manager.broadcast_dashboard(
        {
            "type": "CASE_PINNED",
            "case_id": case_id,
            "pinned": request.pinned,
        }
    )
    return {"case_id": case_id, "pinned": request.pinned}


@router.delete("/cases/{case_id}", response_model=DeleteCaseResponse)
async def delete_case(case_id: str, lawyer_id: int = Depends(get_current_lawyer)):
    await verify_ownership(case_id, lawyer_id)
    logger.info(f"Delete case {case_id}")
    try:
        await intake.delete(case_id)
        await lawyer.delete(case_id)
    except Exception as e:
        logger.error(f"Error deleting case {case_id}: {e}")
        raise HTTPException(status_code=502, detail="Service unavailable")
    await manager.broadcast_dashboard(
        {
            "type": "CASE_DELETED",
            "case_id": case_id,
        }
    )
    await manager.close_case_connections(case_id)
    return {"case_id": case_id, "deleted": True}
