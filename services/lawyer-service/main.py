from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
from core.llm import get_llm
from core.logger import logger
from langchain_core.prompts import ChatPromptTemplate
try:
    from langchain_tavily import TavilySearchResults
except ImportError:
    from langchain_community.tools.tavily_search import TavilySearchResults
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
    search_web: bool = False

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

        search_results = ""
        if request.search_web:
            logger.info(f"Web search enabled for case_id={request.case_id}")
            try:
                search = TavilySearchResults(max_results=5)
                raw_results = search.invoke(request.query)
                search_results = "\n\n".join(
                    [f"**{r.get('title','')}**\n{r.get('content','')}\n[{r.get('url','')}]" for r in raw_results]
                )
                logger.info(f"Web search completed for case_id={request.case_id}, results={len(raw_results)}")
            except Exception as e:
                logger.warning(f"Web search failed for case_id={request.case_id}: {e}")
                search_results = ""

        search_results_section = ""
        if search_results:
            search_results_section = f"РЕЗУЛЬТАТЫ ПОИСКА В ИНТЕРНЕТЕ:\n{search_results}"

        logger.info(f"Invoking LLM for case_id={request.case_id}")
        llm = get_llm()
        prompt = ChatPromptTemplate.from_template(ASSISTANT_PROMPT)
        chain = prompt | llm
        
        response = chain.invoke({
            "case_file": request.case_file or "Не указано.",
            "history": full_context_history,
            "query": request.query,
            "search_results_section": search_results_section
        })
        
        # 3. Сохраняем ответ ассистента
        ai_msg = Message(case_id=request.case_id, sender_role="ai_case", content=response.content, source="frontend")
        session.add(ai_msg)
        session.commit()
        
        logger.info(f"LLM analysis completed for case_id={request.case_id}")
        return {"response": response.content}
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
