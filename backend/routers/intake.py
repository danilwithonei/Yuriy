import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from auth import get_current_lawyer
from core.logger import logger
from routers.deps import intake, verify_ownership

router = APIRouter()


class AssistRequest(BaseModel):
    message: str


@router.post("/cases/{case_id}/intake/chat")
async def intake_chat(case_id: str, request: AssistRequest, lawyer_id: int = Depends(get_current_lawyer)):
    await verify_ownership(case_id, lawyer_id)
    logger.info(f"Intake chat for case_id={case_id}: {request.message[:50]}...")

    async def generate():
        async for data in intake.chat_stream(case_id, request.message):
            if "error" in data:
                yield f"data: {json.dumps(data)}\n\n"
                return
            if "response" in data:
                yield f"data: {json.dumps({'response': data.get('response'), 'is_ready': data.get('is_ready', False)})}\n\n"
                continue
            if data.get("done"):
                yield f"data: {json.dumps(data)}\n\n"
                return
            yield f"data: {json.dumps(data)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/cases/{case_id}/intake/confirm")
async def intake_confirm(case_id: str, lawyer_id: int = Depends(get_current_lawyer)):
    await verify_ownership(case_id, lawyer_id)
    logger.info(f"Intake confirm for case_id={case_id}")
    try:
        return await intake.confirm(case_id)
    except Exception as e:
        logger.error(f"Error confirming intake for case {case_id}: {e}")
        raise HTTPException(status_code=502, detail="Intake Service unavailable")
