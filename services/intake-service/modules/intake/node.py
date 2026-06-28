from langchain_core.messages import AIMessage, SystemMessage

from core.llm import llm
from core.state import AgentState

from .prompts import INTAKE_SYSTEM_PROMPT


async def intake_node(state: AgentState):
    system_msg = SystemMessage(content=INTAKE_SYSTEM_PROMPT)

    full = ""
    async for chunk in llm.astream([system_msg] + state["messages"]):
        if chunk.content:
            full += chunk.content

    lines = full.strip().split("\n")
    is_ready = False
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[IS_READY:"):
            is_ready = "true" in stripped.lower()
        else:
            clean_lines.append(line)

    answer = "\n".join(clean_lines)
    return {"messages": [AIMessage(content=answer)], "is_ready": is_ready}
