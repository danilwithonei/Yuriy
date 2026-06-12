from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from database import create_db_and_tables, get_session
from models import User, Case, Message
from pydantic import BaseModel
from typing import Optional, List
from graph import app_graph
from langchain_core.messages import HumanMessage
import os
import uvicorn

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

def run_research_background(case_id: int, config: dict):
    from database import engine
    from sqlmodel import Session
    from models import Case
    from graph import app_graph
    
    with Session(engine) as session:
        # Продолжаем выполнение графа с прерванного места (research)
        output = app_graph.invoke(None, config=config)
        
        current_case = session.get(Case, case_id)
        if current_case and output and output.get("case_file"):
            current_case.case_file = output["case_file"]
            current_case.status = "ready"
            session.add(current_case)
            session.commit()

@app.post("/chat")
def chat(request: ChatRequest, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    # 1. Get or create case
    if not request.case_id:
        # For simplicity, ensure user exists or create dummy
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
    else:
        case_id = request.case_id
        case = session.get(Case, case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
    
    # 2. Save human message to DB
    msg = Message(case_id=case_id, sender_role="client", content=request.message)
    session.add(msg)
    session.commit()
    
    # 3. Run LangGraph (it will pause before 'research' if confirmed)
    config = {"configurable": {"thread_id": str(case_id)}}
    input_state = {
        "messages": [HumanMessage(content=request.message)],
        "case_id": case_id
    }
    
    output = app_graph.invoke(input_state, config=config)
    
    # 4. Save AI response to DB
    ai_msg_content = output["messages"][-1].content
    ai_msg = Message(case_id=case_id, sender_role="ai_intake", content=ai_msg_content)
    session.add(ai_msg)
    
    # 5. Check if the graph paused before research
    current_case = session.get(Case, case_id)
    state = app_graph.get_state(config)
    
    if state.next and "research" in state.next:
        current_case.status = "researching"
        background_tasks.add_task(run_research_background, case_id, config)
    elif output.get("case_file"): # Fallback just in case
        current_case.case_file = output["case_file"]
        current_case.status = "ready"
        
    session.add(current_case)
    session.commit()
    
    return {
        "case_id": case_id,
        "response": ai_msg_content,
        "status": current_case.status
    }

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
