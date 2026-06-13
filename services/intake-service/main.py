from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlmodel import Session, select
from typing import Optional, List
import os
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

async def run_research_task(case_id: int):
    """Фоновая задача для исследования."""
    logger.info(f"Background research started for case_id={case_id}")
    output = await AgentService.run_background_research(case_id)
    with Session(engine) as session:
        case = session.get(Case, case_id)
        if case and output.get("case_file"):
            case.case_file = output["case_file"]
            case.status = "ready"
            session.add(case)
            session.commit()
            logger.info(f"Research completed and case_file saved for case_id={case_id}")

class ChatRequest(BaseModel):
    user_id: int
    case_id: Optional[int] = None
    message: str

@app.post("/chat")
async def chat(request: ChatRequest, session: Session = Depends(get_session)):
    case_id = request.case_id
    logger.info(f"Chat request received for user_id={request.user_id}, case_id={case_id}")
    
    # Логика получения/создания дела
    if not case_id:
        user = session.exec(select(User).where(User.id == request.user_id)).first()
        if not user:
            user = User(id=request.user_id, username=f"user_{request.user_id}", role="client")
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info(f"Created new user: {user.username}")
        
        case = Case(client_id=request.user_id)
        session.add(case)
        session.commit()
        session.refresh(case)
        case_id = case.id
        logger.info(f"Created new case with id={case_id}")
    
    # Сохраняем сообщение
    msg = Message(case_id=case_id, sender_role="client", content=request.message)
    session.add(msg)
    session.commit()

    # Работаем с графом через сервис
    logger.info(f"Invoking graph for case_id={case_id}")
    output, is_ready = await AgentService.handle_user_message(case_id, request.message)
    
    # Сохраняем ответ ИИ
    ai_msg_content = output["messages"][-1].content
    ai_msg = Message(case_id=case_id, sender_role="ai_intake", content=ai_msg_content)
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
    case_id: int

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
async def list_cases(session: Session = Depends(get_session)):
    logger.info("Intake Service: list_cases called")
    return session.exec(select(Case)).all()

@app.get("/case/{case_id}")
async def get_case_status(case_id: int, session: Session = Depends(get_session)):
    logger.info(f"Intake Service: get_case_status for id={case_id}")
    case = session.get(Case, case_id)
    if not case:
        logger.warning(f"Case {case_id} not found")
        raise HTTPException(status_code=404, detail="Case not found")
    messages = session.exec(select(Message).where(Message.case_id == case_id)).all()
    return {"case": case, "messages": messages}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
