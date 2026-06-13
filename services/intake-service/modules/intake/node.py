from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, AIMessage
from .prompts import INTAKE_SYSTEM_PROMPT
from core.llm import llm
from core.state import AgentState

class IntakeResponse(BaseModel):
    """Ответ ассистента клиенту и оценка готовности данных."""
    answer: str = Field(description="Текст ответа пользователю (уточняющий вопрос или подтверждение)")
    is_ready: bool = Field(description="True, если собрано достаточно данных для передачи юристу")

def intake_node(state: AgentState):
    """
    Узел приема заявок. Собирает информацию и определяет готовность.
    """
    system_msg = SystemMessage(content=INTAKE_SYSTEM_PROMPT)
    
    # Принуждаем LLM возвращать структурированный ответ
    structured_llm = llm.with_structured_output(IntakeResponse)
    
    # Добавляем явное указание на JSON в конец списка сообщений
    result = structured_llm.invoke([system_msg] + state["messages"])
    
    return {
        "messages": [AIMessage(content=result.answer)],
        "is_ready": result.is_ready
    }
