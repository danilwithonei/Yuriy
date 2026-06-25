from typing import Annotated, List, TypedDict, Dict, Any
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[List, add_messages]
    case_id: str
    is_ready: bool # ИИ считает, что информации достаточно
    is_confirmed: bool # Юрист/Клиент подтвердил отправку нажатием кнопки
    extracted_data: Dict[str, Any]
    research_results: str
    case_file: str
    case_title: str
    case_summary: str
