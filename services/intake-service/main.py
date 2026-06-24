from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlmodel import Session, select
from typing import Optional, List
import os
import httpx
import uvicorn

# Импорты из локальных модулей сервиса
from models import User, Case, Message
from database import engine, create_db_and_tables, get_session
from core.agent import AgentService
from core.logger import logger

app = FastAPI(title="Yuriy Agent Service")

@app.on_event("startup")
def on_startup():
    logger.info("Starting Intake Agent Service")
    os.makedirs("./db", exist_ok=True)
    create_db_and_tables()
    _seed_default_lawyer()

def _seed_default_lawyer():
    with Session(engine) as session:
        existing = session.exec(
            select(User).where(User.external_id == "lawyer_default", User.source == "frontend")
        ).first()
        if existing:
            return
        user = User(
            external_id="lawyer_default",
            source="frontend",
            username="lawyer_default",
            role="lawyer"
        )
        session.add(user)
        session.commit()
        logger.info("Seeded default lawyer user")

async def _notify_gateway(case_id: str, status: str):
    gateway_url = os.getenv("GATEWAY_URL", "http://backend:8000")
    async with httpx.AsyncClient() as client:
        try:
            await client.post(f"{gateway_url}/internal/case-updated", json={
                "case_id": case_id, "status": status
            }, timeout=5.0)
            logger.info(f"Gateway notified: case {case_id} -> {status}")
        except Exception as e:
            logger.warning(f"Failed to notify gateway for case {case_id}: {e}")

async def run_research_task(case_id: str):
    """Фоновая задача для исследования."""
    logger.info(f"Background research started for case_id={case_id}")
    try:
        output = await AgentService.run_background_research(case_id)
    except Exception as e:
        logger.error(f"Research failed for case_id={case_id}: {e}")
        output = {}
    with Session(engine) as session:
        case = session.get(Case, case_id)
        if case:
            if output.get("case_file"):
                case.case_file = output["case_file"]
                case.status = "ready"
                logger.info(f"Research completed for case_id={case_id}")
            else:
                messages = session.exec(select(Message).where(Message.case_id == case_id)).all()
                summary = "\n".join([f"{m.sender_role}: {m.content}" for m in messages])
                case.case_file = f"Исследование не завершилось, собранные данные:\n\n{summary}"
                case.status = "ready"
                logger.warning(f"Research incomplete, fallback for case_id={case_id}")
            session.add(case)
            session.commit()
            await _notify_gateway(case_id, "ready")

class CreateCaseRequest(BaseModel):
    case_type: str = "intake"
    source: str = "frontend"
    external_id: str = "lawyer_default"
    lawyer_id: Optional[int] = None

class ChatRequest(BaseModel):
    external_id: str
    source: str
    case_id: Optional[str] = None
    message: str
    case_type: Optional[str] = None

@app.post("/create-case")
async def create_case(request: CreateCaseRequest, session: Session = Depends(get_session)):
    logger.info(f"Create case request: type={request.case_type}, source={request.source}")

    user = session.exec(
        select(User).where(User.external_id == request.external_id, User.source == request.source)
    ).first()
    if not user:
        user = User(
            external_id=request.external_id,
            source=request.source,
            username=f"{request.source}_{request.external_id}",
            role="lawyer"
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        logger.info(f"Created user for case creation: {user.username}")

    case = Case(client_id=user.id, source=request.source, case_type=request.case_type, lawyer_id=request.lawyer_id)
    session.add(case)
    session.commit()
    session.refresh(case)
    logger.info(f"Created case id={case.id}, type={request.case_type}, lawyer_id={request.lawyer_id}")

    return {"case_id": case.id, "case_type": request.case_type, "lawyer_id": request.lawyer_id}

@app.post("/chat")
async def chat(request: ChatRequest, session: Session = Depends(get_session)):
    case_id = request.case_id
    logger.info(f"Chat request received for external_id={request.external_id}, source={request.source}, case_id={case_id}")

    # Для direct-дела не запускаем граф, только сохраняем сообщение
    if case_id:
        existing_case = session.get(Case, case_id)
        if existing_case and existing_case.case_type == "direct":
            msg = Message(case_id=case_id, sender_role="client", content=request.message, source=request.source)
            session.add(msg)
            session.commit()
            logger.info(f"Direct case {case_id}: message saved, graph skipped")
            return {
                "case_id": case_id,
                "response": None,
                "is_ready": False,
                "status": "open"
            }
    
    # Логика получения/создания пользователя
    user = session.exec(
        select(User).where(User.external_id == request.external_id, User.source == request.source)
    ).first()
    
    if not user:
        user = User(
            external_id=request.external_id, 
            source=request.source, 
            username=f"{request.source}_{request.external_id}", 
            role="client"
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        logger.info(f"Created new user: {user.username}")

    # Логика получения/создания дела
    case_type = request.case_type or "intake"
    if not case_id:
        case = Case(client_id=user.id, source=request.source, case_type=case_type)
        session.add(case)
        session.commit()
        session.refresh(case)
        case_id = case.id
        logger.info(f"Created new case with id={case_id}")
    
    # Сохраняем сообщение
    msg = Message(case_id=case_id, sender_role="client", content=request.message, source=request.source)
    session.add(msg)
    session.commit()

    # Работаем с графом через сервис
    logger.info(f"Invoking graph for case_id={case_id}")
    output, is_ready = await AgentService.handle_user_message(case_id, request.message)
    
    # Сохраняем ответ ИИ
    ai_msg_content = output["messages"][-1].content
    ai_msg = Message(case_id=case_id, sender_role="ai_intake", content=ai_msg_content, source=request.source)
    session.add(ai_msg)
    session.commit()

    logger.info(f"Graph execution paused. is_ready={is_ready}")

    return {
        "case_id": case_id,
        "response": ai_msg_content,
        "is_ready": is_ready,
        "status": "collecting"
    }

class ConfirmRequest(BaseModel):
    case_id: str

@app.post("/confirm")
async def confirm(request: ConfirmRequest, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    case_id = request.case_id
    logger.info(f"Confirmation received for case_id={case_id}")
    case = session.get(Case, case_id)
    if not case:
        logger.warning(f"Confirm failed: Case {case_id} not found")
        raise HTTPException(status_code=404, detail="Case not found")
    
    await AgentService.confirm_and_resume(case_id)
    case.status = "researching"
    session.add(case)
    session.commit()
    
    logger.info(f"Case {case_id} status updated to researching. Triggering background task.")
    background_tasks.add_task(run_research_task, case_id)
    return {"status": "researching"}

@app.get("/cases", response_model=List[Case])
async def list_cases(lawyer_id: Optional[int] = None, session: Session = Depends(get_session)):
    logger.info(f"Intake Service: list_cases called, lawyer_id={lawyer_id}")
    query = select(Case)
    if lawyer_id is not None:
        query = query.where(Case.lawyer_id == lawyer_id)
    return session.exec(query).all()

@app.get("/case/{case_id}")
async def get_case_status(case_id: str, session: Session = Depends(get_session)):
    logger.info(f"Intake Service: get_case_status for id={case_id}")
    case = session.get(Case, case_id)
    if not case:
        logger.warning(f"Case {case_id} not found")
        raise HTTPException(status_code=404, detail="Case not found")
    messages = session.exec(select(Message).where(Message.case_id == case_id)).all()
    return {"case": case, "messages": messages}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
