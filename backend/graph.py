import os
from typing import Annotated, List, TypedDict, Dict, Any
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv()

class AgentState(TypedDict):
    messages: Annotated[List, add_messages]
    case_id: int
    is_confirmed: bool
    extracted_data: Dict[str, Any]
    research_results: str
    case_file: str

from research import perform_legal_research, analyze_case_intake
from langchain_core.prompts import ChatPromptTemplate

# Используем OpenAI-совместимый эндпоинт Aliyun MaaS
llm = ChatOpenAI(
    model=os.getenv("LLM_MODEL", "qwen3.7-plus"),
    openai_api_key=os.getenv("DASHSCOPE_API_KEY"),
    openai_api_base="https://ws-8xsmg0t4kftupsd5.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
)


def intake_node(state: AgentState):
    system_msg = SystemMessage(content=(
        "You are an AI Lawyer Intake Assistant. Your goal is to interview the client "
        "to gather all necessary information about their legal problem. "
        "Be empathetic, professional, and thorough. "
        "Once you have enough information, ask the client for clear confirmation to 'submit' or 'form' the request. "
        "If the client confirms (e.g., says 'yes, submit', 'сформировать заявку'), set the 'is_confirmed' flag. "
        "Always respond in Russian if the user speaks Russian."
    ))
    
    response = llm.invoke([system_msg] + state["messages"])
    
    # Simple logic to detect confirmation for now
    last_user_msg = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_user_msg = msg.content.lower()
            break
            
    is_confirmed = False
    if "сформировать" in last_user_msg or "подтверждаю" in last_user_msg or "submit" in last_user_msg:
        is_confirmed = True
        
    return {"messages": [response], "is_confirmed": is_confirmed}

def should_continue(state: AgentState):
    if state["is_confirmed"]:
        return "research"
    return END

def research_node(state: AgentState):
    print("--- RESEARCHING ---")
    transcript = "\n".join([f"{m.type}: {m.content}" for m in state["messages"]])
    query = analyze_case_intake(transcript)
    results = perform_legal_research(query)
    return {"research_results": results}

def compiler_node(state: AgentState):
    print("--- COMPILING ---")
    transcript = "\n".join([f"{m.type}: {m.content}" for m in state["messages"]])
    
    prompt = ChatPromptTemplate.from_template("""
    Составьте итоговое "Досье дела" на основе переписки с клиентом и результатов исследования.
    
    Переписка: {transcript}
    
    Результаты исследования: {research}
    
    Досье должно быть в формате Markdown, содержать:
    1. Суть проблемы.
    2. Ключевые факты.
    3. Применимое законодательство (на основе исследования).
    4. Рекомендации для юриста.
    """)
    
    chain = prompt | llm
    case_file = chain.invoke({"transcript": transcript, "research": state["research_results"]})
    return {"case_file": case_file.content}

# Build the graph
workflow = StateGraph(AgentState)

workflow.add_node("intake", intake_node)
workflow.add_node("research", research_node)
workflow.add_node("compiler", compiler_node)

workflow.add_edge(START, "intake")
workflow.add_conditional_edges("intake", should_continue, {"research": "research", END: END})
workflow.add_edge("research", "compiler")
workflow.add_edge("compiler", END)

from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()
app_graph = workflow.compile(checkpointer=memory)
