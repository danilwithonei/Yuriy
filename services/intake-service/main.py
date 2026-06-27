from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select, text
from typing import Optional, List
from datetime import datetime
import os
import json
import httpx
import uvicorn

# Импорты из локальных модулей сервиса
from models import User, Case, Message
from database import engine, create_db_and_tables, get_session
from core.agent import AgentService
from core.logger import logger

app = FastAPI(title="Yuriy Agent Service")

def _migrate_schema():
    """Добавляет новые колонки в существующие таблицы (SQLite)."""
    with Session(engine) as session:
        for stmt in [
            'ALTER TABLE "case" ADD COLUMN pinned BOOLEAN DEFAULT 0',
            'ALTER TABLE "case" ADD COLUMN deleted_at TIMESTAMP',
        ]:
            try:
                session.exec(text(stmt))
                session.commit()
                logger.info(f"Migration: {stmt}")
            except Exception as e:
                session.rollback()
                logger.warning(f"Migration skipped (already exists?): {e}")

@app.on_event("startup")
def on_startup():
    logger.info("Starting Intake Agent Service")
    os.makedirs("./db", exist_ok=True)
    create_db_and_tables()
    _migrate_schema()
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

async def _notify_gateway(case_id: str, status: str, title: str | None = None, summary: str | None = None):
    gateway_url = os.getenv("GATEWAY_URL", "http://backend:8000")
    async with httpx.AsyncClient() as client:
        try:
            body = {"case_id": case_id, "status": status}
            if title is not None:
                body["title"] = title
            if summary is not None:
                body["summary"] = summary
            await client.post(f"{gateway_url}/internal/case-updated", json=body, timeout=5.0)
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
                case.title = output.get("case_title") or case.title
                case.summary = output.get("case_summary")
                case.status = "ready"
                logger.info(f"Research completed for case_id={case_id}")
            else:
                messages = session.exec(select(Message).where(Message.case_id == case_id)).all()
                fallback = "\n".join([f"{m.sender_role}: {m.content}" for m in messages])
                case.case_file = f"Исследование не завершилось, собранные данные:\n\n{fallback}"
                case.status = "ready"
                logger.warning(f"Research incomplete, fallback for case_id={case_id}")
            session.add(case)
            session.commit()
            await _notify_gateway(case_id, "ready", title=case.title, summary=case.summary)

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
            if not existing_case.title:
                existing_case.title = request.message[:50]
                session.add(existing_case)
                session.commit()
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
        # Предзаполняем title из первого сообщения как временный
        case.title = request.message[:50]
        session.add(case)
        session.commit()
        logger.info(f"Created new case with id={case_id}")
    
    # Сохраняем сообщение клиента
    msg = Message(case_id=case_id, sender_role="client", content=request.message, source=request.source)
    session.add(msg)
    session.commit()

    logger.info(f"Streaming from Intake Agent for case_id={case_id}")

    async def generate():
        full_response = ""
        stream_count = 0
        try:
            async for event in AgentService.handle_user_message_stream(case_id, request.message):
                kind = event[0]
                if kind == "token":
                    token = event[1]
                    full_response += token
                    stream_count += 1
                    if stream_count % 5 == 0:
                        logger.info(f"Intake token #{stream_count} for case_id={case_id} (+{len(token)} chars, total {len(full_response)})")
                    yield f"data: {json.dumps({'token': token})}\n\n"
                elif kind == "result":
                    _, (output, is_ready) = event
                    logger.info(f"Intake stream done for case_id={case_id}: {stream_count} events, {len(full_response)} chars, is_ready={is_ready}")
                    # Сохраняем ответ ИИ в отдельной сессии
                    ai_msg_content = output["messages"][-1].content
                    try:
                        with Session(engine) as save_session:
                            ai_msg = Message(case_id=case_id, sender_role="ai_intake", content=ai_msg_content, source=request.source)
                            save_session.add(ai_msg)
                            save_session.commit()
                        logger.info(f"AI intake message saved for case_id={case_id}")
                    except Exception as e:
                        logger.error(f"Failed to save AI intake message for case_id={case_id}: {e}")
                    yield f"data: {json.dumps({'done': True, 'is_ready': is_ready})}\n\n"
        except Exception as e:
            logger.error(f"Intake streaming failed for case_id={case_id}: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

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
    await _notify_gateway(case_id, "researching", title=case.title, summary=case.summary)
    return {"status": "researching"}

@app.get("/cases", response_model=List[Case])
async def list_cases(lawyer_id: Optional[int] = None, session: Session = Depends(get_session)):
    logger.info(f"Intake Service: list_cases called, lawyer_id={lawyer_id}")
    query = select(Case).where(Case.deleted_at == None)
    if lawyer_id is not None:
        query = query.where(Case.lawyer_id == lawyer_id)
    return session.exec(query).all()

@app.get("/case/{case_id}")
async def get_case_status(case_id: str, session: Session = Depends(get_session)):
    logger.info(f"Intake Service: get_case_status for id={case_id}")
    case = session.get(Case, case_id)
    if not case or case.deleted_at is not None:
        logger.warning(f"Case {case_id} not found")
        raise HTTPException(status_code=404, detail="Case not found")
    messages = session.exec(select(Message).where(Message.case_id == case_id)).all()
    return {"case": case, "messages": messages}

class PatchCasePinRequest(BaseModel):
    pinned: bool

@app.patch("/case/{case_id}/pin")
async def patch_case_pin(case_id: str, request: PatchCasePinRequest, session: Session = Depends(get_session)):
    logger.info(f"Intake Service: pin case id={case_id}, pinned={request.pinned}")
    case = session.get(Case, case_id)
    if not case or case.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Case not found")
    case.pinned = request.pinned
    session.add(case)
    session.commit()
    return {"case_id": case_id, "pinned": case.pinned}

@app.delete("/case/{case_id}")
async def delete_case(case_id: str, session: Session = Depends(get_session)):
    logger.info(f"Intake Service: soft delete case id={case_id}")
    case = session.get(Case, case_id)
    if not case or case.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Case not found")
    case.deleted_at = datetime.utcnow()
    session.add(case)
    session.commit()
    return {"case_id": case_id, "deleted": True}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
