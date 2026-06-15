from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
from core.llm import get_llm
from core.logger import logger
from langchain_core.prompts import ChatPromptTemplate
from prompts import ASSISTANT_PROMPT
from models import Message, Case
from database import create_db_and_tables, get_session
import os
import uvicorn

app = FastAPI(title="Yuriy Lawyer Assistant Service")

@app.on_event("startup")
def on_startup():
    logger.info("Starting Lawyer Assistant Service")
    os.makedirs("./db", exist_ok=True)
    create_db_and_tables()

class AssistRequest(BaseModel):
    case_id: int
    case_file: str
    history: str # История из Intake Service (клиент-агент)
    query: str

@app.get("/")
def read_root():
    logger.info("Lawyer Assistant Health check")
    return {"message": "Lawyer Assistant Service is running"}

@app.post("/analyze")
async def analyze_case(request: AssistRequest, session: Session = Depends(get_session)):
    """
    Анализирует материалы дела, сохраняет вопрос юриста и возвращает ответ.
    """
    logger.info(f"Analyze request for case_id={request.case_id}")
    try:
        # 1. Сохраняем вопрос юриста в локальную БД ассистента
        user_msg = Message(case_id=request.case_id, sender_role="lawyer", content=request.query, source="frontend")
        session.add(user_msg)
        session.commit()

        # 2. Получаем историю предыдущих диалогов Юрист-Ассистент из локальной БД
        lawyer_ai_messages = session.exec(
            select(Message).where(Message.case_id == request.case_id)
        ).all()
        
        # Формируем полный контекст для LLM
        lawyer_history_str = "\n".join([f"{m.sender_role}: {m.content}" for m in lawyer_ai_messages[:-1]])
        
        full_context_history = f"--- КЛИЕНТ-ИНТЕРВЬЮ ---\n{request.history}\n\n--- ДИАЛОГ С ЮРИСТОМ ---\n{lawyer_history_str}"

        logger.info(f"Invoking LLM for case_id={request.case_id}")
        llm = get_llm()
        
        from langgraph.prebuilt import create_react_agent
        from langchain_community.tools.tavily_search import TavilySearchResults
        from langchain_core.messages import HumanMessage
        
        system_message = ASSISTANT_PROMPT.format(
            case_file=request.case_file,
            history=full_context_history
        )
        
        tools = []
        if os.getenv("TAVILY_API_KEY"):
            tools.append(TavilySearchResults(max_results=3))
            
        agent = create_react_agent(llm, tools, state_modifier=system_message)
        
        result = agent.invoke({"messages": [HumanMessage(content=request.query)]})
        final_response = result["messages"][-1].content
        
        # 3. Сохраняем ответ ассистента
        ai_msg = Message(case_id=request.case_id, sender_role="ai_case", content=final_response, source="frontend")
        session.add(ai_msg)
        session.commit()
        
        logger.info(f"LLM analysis completed for case_id={request.case_id}")
        return {"response": final_response}
    except Exception as e:
        logger.error(f"Error during analysis for case_id={request.case_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/messages/{case_id}")
async def get_messages(case_id: int, session: Session = Depends(get_session)):
    """Возвращает историю переписки юриста с ассистентом."""
    logger.info(f"Fetching lawyer messages for case_id={case_id}")
    messages = session.exec(select(Message).where(Message.case_id == case_id)).all()
    return messages

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
