from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_lawyer
from core.logger import logger
from routers.deps import lawyer, verify_ownership

router = APIRouter()


class AssistRequest(BaseModel):
    message: str


@router.post("/cases/{case_id}/assist")
async def assist_case(case_id: str, request: AssistRequest, lawyer_id: int = Depends(get_current_lawyer)):
    logger.info(f"Manual assist request for case_id={case_id}")
    case_data = await verify_ownership(case_id, lawyer_id)

    case_file = case_data["case"].get("case_file") or "Досье еще не сформировано."
    history = "\n".join([f"{m['sender_role']}: {m['content']}" for m in case_data["messages"]])

    try:
        full_content = ""
        async for data in lawyer.analyze_stream(case_id, case_file, history, request.message):
            if "token" in data:
                full_content += data["token"]
            elif "error" in data:
                raise HTTPException(status_code=502, detail=data["error"])
            elif data.get("done"):
                break
        return {"response": full_content}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in manual assist for case {case_id}: {e}")
        raise HTTPException(status_code=502, detail="Lawyer Assistant Service unavailable")
