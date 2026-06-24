from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Session
from ws_manager import manager
from core.logger import logger
import os
import uvicorn
import httpx

from database import engine, create_db_and_tables
from models import Lawyer
from schemas import RegisterRequest, LoginRequest, AuthResponse, LawyerOut
from auth import (
    hash_password, verify_password, create_token, decode_token,
    validate_email, get_lawyer_by_email, get_current_lawyer, get_lawyer_or_none
)

app = FastAPI(title="Yuriy Lawyer Dashboard Gateway")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

INTAKE_SERVICE_URL = os.getenv("INTAKE_SERVICE_URL", "http://intake-agent:8001")
LAWYER_SERVICE_URL = os.getenv("LAWYER_SERVICE_URL", "http://lawyer-service:8002")

class CaseUpdatedRequest(BaseModel):
    case_id: str
    status: str

class CreateCaseRequest(BaseModel):
    type: str = "direct"

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/")
def read_root():
    logger.info("Health check endpoint called")
    return {"message": "Lawyer Dashboard Gateway is running"}

@app.post("/internal/case-updated")
async def case_updated(request: CaseUpdatedRequest):
    logger.info(f"Case {request.case_id} status updated to {request.status}, broadcasting")
    await manager.broadcast_dashboard({
        "type": "CASE_STATUS_UPDATED",
        "case_id": request.case_id,
        "status": request.status
    })
    return {"ok": True}

# ─── Auth endpoints ───────────────────────────────────────────────

@app.post("/auth/register")
async def register(request: RegisterRequest):
    email_err = validate_email(request.email)
    if email_err:
        raise HTTPException(status_code=400, detail=email_err)
    if len(request.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")
    with Session(engine) as session:
        existing = get_lawyer_by_email(session, request.email)
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")
        lawyer = Lawyer(
            email=request.email,
            name=request.name,
            password_hash=hash_password(request.password)
        )
        session.add(lawyer)
        session.commit()
        session.refresh(lawyer)
    token = create_token(lawyer.id)
    return AuthResponse(token=token, lawyer=LawyerOut(id=lawyer.id, email=lawyer.email, name=lawyer.name))

@app.post("/auth/login")
async def login(request: LoginRequest):
    with Session(engine) as session:
        lawyer = get_lawyer_by_email(session, request.email)
        if not lawyer or not verify_password(request.password, lawyer.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(lawyer.id)
    return AuthResponse(token=token, lawyer=LawyerOut(id=lawyer.id, email=lawyer.email, name=lawyer.name))

@app.get("/auth/me")
async def me(lawyer_id: int = Depends(get_current_lawyer)):
    with Session(engine) as session:
        lawyer = session.get(Lawyer, lawyer_id)
        if not lawyer:
            raise HTTPException(status_code=404, detail="Lawyer not found")
        return LawyerOut(id=lawyer.id, email=lawyer.email, name=lawyer.name)

class AssistRequest(BaseModel):
    message: str

async def _verify_ownership(case_id: str, lawyer_id: int,
                            client: httpx.AsyncClient | None = None) -> dict:
    if client is None:
        async with httpx.AsyncClient() as cl:
            return await _verify_ownership(case_id, lawyer_id, client=cl)
    try:
        res = await client.get(f"{INTAKE_SERVICE_URL}/case/{case_id}")
        if res.status_code != 200:
            raise HTTPException(status_code=404, detail="Case not found")
        case_data = res.json()
        case_lawyer_id = case_data["case"].get("lawyer_id")
        if case_lawyer_id is not None and case_lawyer_id != lawyer_id:
            raise HTTPException(status_code=403, detail="Access denied")
        return case_data
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Intake Service unavailable")

@app.post("/cases")
async def create_case(request: CreateCaseRequest, lawyer_id: int = Depends(get_current_lawyer)):
    logger.info(f"Create case request: type={request.type}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{INTAKE_SERVICE_URL}/create-case", json={
                "case_type": request.type,
                "source": "frontend",
                "lawyer_id": lawyer_id
            })
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Failed to create case")
            return response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="Intake Service unavailable")
        except Exception as e:
            logger.error(f"Error creating case: {e}")
            raise HTTPException(status_code=502, detail=f"Service Error: {str(e)}")

@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return
    lawyer_id = get_lawyer_or_none(token)
    if lawyer_id is None:
        await websocket.close(code=4001)
        return
    await manager.connect_dashboard(websocket)
    logger.info(f"Dashboard WebSocket connected for lawyer_id={lawyer_id}")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_dashboard(websocket)
        logger.info(f"Dashboard WebSocket disconnected for lawyer_id={lawyer_id}")

@app.websocket("/ws/cases/{case_id}/chat")
async def websocket_case_chat(websocket: WebSocket, case_id: str):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return
    lawyer_id = get_lawyer_or_none(token)
    if lawyer_id is None:
        await websocket.close(code=4001)
        return
    async with httpx.AsyncClient() as client:
        try:
            case_data = await _verify_ownership(case_id, lawyer_id, client=client)
        except HTTPException as e:
            code = {404: 4004, 403: 4003}.get(e.status_code, 4002)
            await websocket.close(code=code)
            return
        await manager.connect_case(case_id, websocket)
        logger.info(f"Case chat WebSocket connected for case_id={case_id}, lawyer_id={lawyer_id}")
        try:
            while True:
                try:
                    data = await websocket.receive_json()
                except WebSocketDisconnect:
                    raise
                except Exception as e:
                    logger.warning(f"Invalid JSON received on WebSocket case_id={case_id}: {e}")
                    try:
                        await websocket.send_json({"type": "AI_ERROR", "error": "Invalid JSON format"})
                    except Exception:
                        pass
                    continue

                message_text = data.get("message")
                if message_text:
                    logger.info(f"Received WS message for case_id={case_id}: {message_text[:50]}...")
                    case_type = case_data["case"].get("case_type", "intake")
                    is_direct = case_type == "direct"
                    if is_direct:
                        case_file = ""
                        intake_history = ""
                    else:
                        case_file = case_data["case"].get("case_file") or "Досье еще не сформировано."
                        intake_history = "\n".join([f"{m['sender_role']}: {m['content']}" for m in case_data["messages"]])

                    await manager.send_case_message(case_id, {"type": "AI_THINKING", "sender": "ai_case"})

                    logger.info(f"Calling Lawyer Assistant for case_id={case_id}")
                    try:
                        assist_res = await client.post(f"{LAWYER_SERVICE_URL}/analyze", json={
                            "case_id": case_id,
                            "case_file": case_file,
                            "history": intake_history,
                            "query": message_text,
                            "search_web": is_direct
                        }, timeout=60.0)

                        if assist_res.status_code != 200:
                            error_detail = assist_res.json().get("detail", "Lawyer Assistant Service error")
                            logger.error(f"Lawyer Assistant error for case_id={case_id}: {error_detail}")
                            await manager.send_case_message(case_id, {"type": "AI_ERROR", "error": error_detail})
                            continue

                        assist_data = assist_res.json()
                        ai_content = assist_data.get("response")
                        if not ai_content:
                            logger.error(f"Empty response from Lawyer Assistant for case_id={case_id}")
                            await manager.send_case_message(case_id, {"type": "AI_ERROR", "error": "Empty response from assistant"})
                            continue

                        logger.info(f"AI response received for case_id={case_id}")

                        await manager.send_case_message(case_id, {
                            "type": "AI_RESPONSE",
                            "content": ai_content,
                            "sender": "ai_case"
                        })
                    except Exception as e:
                        logger.error(f"Failed to reach Lawyer Assistant Service: {e}")
                        await manager.send_case_message(case_id, {"type": "AI_ERROR", "error": "Lawyer Assistant Service unavailable"})

        except WebSocketDisconnect:
            manager.disconnect_case(case_id, websocket)
            logger.info(f"Case chat WebSocket disconnected for case_id={case_id}")

@app.get("/cases")
async def list_cases(lawyer_id: int = Depends(get_current_lawyer)):
    logger.info(f"Listing cases for lawyer_id={lawyer_id}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{INTAKE_SERVICE_URL}/cases", params={"lawyer_id": lawyer_id})
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching cases from Intake Service: {e}")
            raise HTTPException(status_code=502, detail=f"Intake Service Error: {str(e)}")

@app.get("/cases/{case_id}")
async def get_case(case_id: str, lawyer_id: int = Depends(get_current_lawyer)):
    logger.info(f"Fetching details for case_id={case_id}")
    intake_data = await _verify_ownership(case_id, lawyer_id)
    async with httpx.AsyncClient() as client:
        try:
            # 1. Запрос к Lawyer Service для получения диалогов Юрист-ИИ
            try:
                lawyer_res = await client.get(f"{LAWYER_SERVICE_URL}/messages/{case_id}")
                lawyer_messages = lawyer_res.json() if lawyer_res.status_code == 200 else []
            except Exception as e:
                logger.warning(f"Could not fetch lawyer messages for case {case_id}: {e}")
                lawyer_messages = []

            # 2. Объединяем сообщения
            all_messages = intake_data["messages"] + lawyer_messages

            return {
                "case": intake_data["case"],
                "messages": all_messages
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error communicating with backend services for case {case_id}: {e}")
            raise HTTPException(status_code=502, detail=f"Service Communication Error: {str(e)}")

@app.post("/cases/{case_id}/assist")
async def assist_case(case_id: str, request: AssistRequest, lawyer_id: int = Depends(get_current_lawyer)):
    logger.info(f"Manual assist request for case_id={case_id}")
    case_data = await _verify_ownership(case_id, lawyer_id)
    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Analyzing case {case_id} for manual assist")
            assist_res = await client.post(f"{LAWYER_SERVICE_URL}/analyze", json={
                "case_id": case_id,
                "case_file": case_data["case"].get("case_file") or "Досье еще не сформировано.",
                "history": "\n".join([f"{m['sender_role']}: {m['content']}" for m in case_data["messages"]]),
                "query": request.message
            }, timeout=60.0)
            
            return assist_res.json()
        except Exception as e:
            logger.error(f"Error in manual assist for case {case_id}: {e}")
            raise HTTPException(status_code=502, detail=f"Service Communication Error: {str(e)}")

@app.post("/cases/{case_id}/intake/chat")
async def intake_chat(case_id: str, request: AssistRequest, lawyer_id: int = Depends(get_current_lawyer)):
    await _verify_ownership(case_id, lawyer_id)
    logger.info(f"Intake chat for case_id={case_id}: {request.message[:50]}...")
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(f"{INTAKE_SERVICE_URL}/chat", json={
                "external_id": "lawyer_default",
                "source": "frontend",
                "case_id": case_id,
                "message": request.message
            }, timeout=120.0)
            if res.status_code != 200:
                error_detail = res.json().get("detail", "Intake Service error")
                raise HTTPException(status_code=502, detail=error_detail)
            return res.json()
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="Intake Service unavailable")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in intake chat for case {case_id}: {e}")
            raise HTTPException(status_code=502, detail=f"Service Error: {str(e)}")

@app.post("/cases/{case_id}/intake/confirm")
async def intake_confirm(case_id: str, lawyer_id: int = Depends(get_current_lawyer)):
    await _verify_ownership(case_id, lawyer_id)
    logger.info(f"Intake confirm for case_id={case_id}")
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(f"{INTAKE_SERVICE_URL}/confirm", json={"case_id": case_id})
            if res.status_code != 200:
                raise HTTPException(status_code=502, detail="Failed to confirm intake")
            return res.json()
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="Intake Service unavailable")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error confirming intake for case {case_id}: {e}")
            raise HTTPException(status_code=502, detail=f"Service Error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
