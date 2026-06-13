from langchain_core.prompts import ChatPromptTemplate
from core.llm import llm
from core.state import AgentState
from .prompts import COMPILER_PROMPT

def compiler_node(state: AgentState):
    """
    Узел графа для компиляции итогового досье.
    """
    print("--- COMPILING ---")
    transcript = "\n".join([f"{m.type}: {m.content}" for m in state["messages"]])
    
    prompt = ChatPromptTemplate.from_template(COMPILER_PROMPT)
    
    chain = prompt | llm
    case_file = chain.invoke({
        "transcript": transcript, 
        "research": state["research_results"]
    })
    return {"case_file": case_file.content}
