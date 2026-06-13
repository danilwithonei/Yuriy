from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from database import create_db_and_tables, get_session
from models import User, Case, Message
from pydantic import BaseModel
from typing import Optional, List
from graph import app_graph
from langchain_core.messages import HumanMessage
from ws_manager import manager
import os
import uvicorn
import asyncio

app = FastAPI(title="AI Lawyer API")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене лучше заменить на конкретный URL фронтенда
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    user_id: int
    case_id: Optional[int] = None
    message: str

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/")
def read_root():
    return {"message": "AI Lawyer API is running"}

async def run_research_background(case_id: int, config: dict):
    from database import engine
    from sqlmodel import Session
    from models import Case
    from graph import app_graph
    
    # Имитация асинхронности для LangGraph invoke (или использование ainvoke)
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, lambda: app_graph.invoke(None, config=config))
    
    with Session(engine) as session:
        current_case = session.get(Case, case_id)
        if current_case and output and output.get("case_file"):
            current_case.case_file = output["case_file"]
            current_case.status = "ready"
            session.add(current_case)
            session.commit()
            
            # Уведомляем фронтенд об обновлении статуса
            await manager.broadcast_dashboard({
                "type": "CASE_STATUS_UPDATED",
                "case_id": case_id,
                "status": "ready"
            })

class ConfirmRequest(BaseModel):
    case_id: int

@app.post("/confirm")
async def confirm_case(request: ConfirmRequest, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    case = session.get(Case, request.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    config = {"configurable": {"thread_id": str(request.case_id)}}
    
    # 1. Обновляем состояние графа вручную
    app_graph.update_state(config, {"is_confirmed": True})
    
    # 2. Меняем статус и запускаем исследование в фоне
    case.status = "researching"
    session.add(case)
    session.commit()
    
    # Уведомляем фронтенд о начале исследования
    await manager.broadcast_dashboard({
        "type": "CASE_STATUS_UPDATED",
        "case_id": request.case_id,
        "status": "researching"
    })
    
    background_tasks.add_task(run_research_background, request.case_id, config)
    
    return {"status": "researching"}

@app.post("/chat")
async def chat(request: ChatRequest, session: Session = Depends(get_session)):
    # 1. Get or create case
    is_new_case = False
    if not request.case_id:
        user = session.exec(select(User).where(User.id == request.user_id)).first()
        if not user:
            user = User(id=request.user_id, username=f"user_{request.user_id}", role="client")
            session.add(user)
            session.commit()
            session.refresh(user)
        
        case = Case(client_id=user.id)
        session.add(case)
        session.commit()
        session.refresh(case)
        case_id = case.id
        is_new_case = True
    else:
        case_id = request.case_id
        case = session.get(Case, case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
    
    # 2. Save human message to DB
    msg = Message(case_id=case_id, sender_role="client", content=request.message)
    session.add(msg)
    session.commit()
    
    # 3. Run LangGraph (it will stop after intake because is_confirmed is False)
    config = {"configurable": {"thread_id": str(case_id)}}
    input_state = {
        "messages": [HumanMessage(content=request.message)],
        "case_id": case_id
    }
    
    loop = asyncio.get_event_loop()
    output = await loop.run_in_executor(None, lambda: app_graph.invoke(input_state, config=config))
    
    # 4. Save AI response to DB
    ai_msg_content = output["messages"][-1].content
    ai_msg = Message(case_id=case_id, sender_role="ai_intake", content=ai_msg_content)
    session.add(ai_msg)
    session.commit()
    
    # Если это новое дело, уведомляем дашборд
    if is_new_case:
        await manager.broadcast_dashboard({
            "type": "CASE_CREATED",
            "case": {
                "id": case.id,
                "client_id": case.client_id,
                "status": case.status,
                "created_at": case.created_at.isoformat() if case.created_at else None
            }
        })
    
    return {
        "case_id": case_id,
        "response": ai_msg_content,
        "status": case.status
    }

@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    await manager.connect_dashboard(websocket)
    try:
        while True:
            # Просто поддерживаем соединение
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_dashboard(websocket)

@app.websocket("/ws/cases/{case_id}/chat")
async def websocket_case_chat(websocket: WebSocket, case_id: int):
    await manager.connect_case(case_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            message_text = data.get("message")
            if message_text:
                # Обработка сообщения через ИИ-ассистента (логика из assist_case)
                from database import engine
                from sqlmodel import Session
                from models import Case, Message
                from langchain_openai import ChatOpenAI
                from langchain_core.prompts import ChatPromptTemplate
                from prompts import ASSISTANT_PROMPT
                
                with Session(engine) as session:
                    case = session.get(Case, case_id)
                    if not case:
                        await websocket.send_json({"error": "Case not found"})
                        continue
                    
                    # Сохраняем сообщение пользователя
                    user_msg = Message(case_id=case_id, sender_role="client", content=message_text)
                    session.add(user_msg)
                    session.commit()

                    # Получаем историю
                    messages = session.exec(select(Message).where(Message.case_id == case_id)).all()
                    history_str = "\n".join([f"{m.sender_role}: {m.content}" for m in messages])
                    
                    # Уведомляем участников, что ИИ начал думать
                    await manager.send_case_message(case_id, {
                        "type": "AI_THINKING",
                        "sender": "ai_case"
                    })

                    llm = ChatOpenAI(
                        model=os.getenv("LLM_MODEL", "qwen3.7-plus"),
                        openai_api_key=os.getenv("DASHSCOPE_API_KEY"),
                        openai_api_base="https://ws-8xsmg0t4kftupsd5.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
                    )

                    prompt = ChatPromptTemplate.from_template(ASSISTANT_PROMPT)
                    chain = prompt | llm
                    
                    # Получаем текущий цикл событий
                    loop = asyncio.get_event_loop()
                    
                    # Имитируем стриминг или просто отправляем ответ (пока просто ответ)
                    response = await loop.run_in_executor(None, lambda: chain.invoke({
                        "case_file": case.case_file or "Досье еще не сформировано.",
                        "history": history_str,
                        "query": message_text
                    }))
                    
                    # Сохраняем ответ ИИ
                    ai_msg = Message(case_id=case_id, sender_role="ai_case", content=response.content)
                    session.add(ai_msg)
                    session.commit()
                    
                    # Отправляем ответ всем подключенным к этому делу
                    await manager.send_case_message(case_id, {
                        "type": "AI_RESPONSE",
                        "content": response.content,
                        "sender": "ai_case"
                    })
    except WebSocketDisconnect:
        manager.disconnect_case(case_id, websocket)
    except Exception as e:
        print(f"WS Error: {e}")
        manager.disconnect_case(case_id, websocket)

@app.get("/cases", response_model=List[Case])
def list_cases(session: Session = Depends(get_session)):
    return session.exec(select(Case)).all()

@app.get("/cases/{case_id}")
def get_case(case_id: int, session: Session = Depends(get_session)):
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    messages = session.exec(select(Message).where(Message.case_id == case_id)).all()
    return {"case": case, "messages": messages}

class AssistRequest(BaseModel):
    message: str

@app.post("/cases/{case_id}/assist")
def assist_case(case_id: int, request: AssistRequest, session: Session = Depends(get_session)):
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # 1. Get history
    messages = session.exec(select(Message).where(Message.case_id == case_id)).all()
    history_str = "\n".join([f"{m.sender_role}: {m.content}" for m in messages])
    
    # 2. Call LLM with full context
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from prompts import ASSISTANT_PROMPT
    
    llm = ChatOpenAI(
        model=os.getenv("LLM_MODEL", "qwen3.7-plus"),
        openai_api_key=os.getenv("DASHSCOPE_API_KEY"),
        openai_api_base="https://ws-8xsmg0t4kftupsd5.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
    )

    prompt = ChatPromptTemplate.from_template(ASSISTANT_PROMPT)
    
    chain = prompt | llm
    response = chain.invoke({
        "case_file": case.case_file or "Досье еще не сформировано.",
        "history": history_str,
        "query": request.message
    })
    
    # 3. Save AI response to DB
    ai_msg = Message(case_id=case_id, sender_role="ai_case", content=response.content)
    session.add(ai_msg)
    session.commit()
    
    return {"response": response.content}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
