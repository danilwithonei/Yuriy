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
from prompts import INTAKE_SYSTEM_PROMPT, COMPILER_PROMPT, INTENT_EVALUATION_PROMPT

# Используем OpenAI-совместимый эндпоинт Aliyun MaaS
llm = ChatOpenAI(
    model=os.getenv("LLM_MODEL", "qwen3.7-plus"),
    openai_api_key=os.getenv("DASHSCOPE_API_KEY"),
    openai_api_base="https://ws-8xsmg0t4kftupsd5.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
)


def intake_node(state: AgentState):
    system_msg = SystemMessage(content=INTAKE_SYSTEM_PROMPT)
    
    response = llm.invoke([system_msg] + state["messages"])
    
    # Интеллектуальное определение намерения пользователя
    transcript = "\n".join([f"{m.type}: {m.content}" for m in state["messages"]])
    
    eval_prompt = ChatPromptTemplate.from_template(INTENT_EVALUATION_PROMPT)
    eval_chain = eval_prompt | llm
    eval_result = eval_chain.invoke({"transcript": transcript})
    
    is_confirmed = "TRUE" in eval_result.content.upper()
        
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
    
    prompt = ChatPromptTemplate.from_template(COMPILER_PROMPT)
    
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
