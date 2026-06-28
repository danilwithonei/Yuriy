import json
import re

from langchain_core.prompts import ChatPromptTemplate

from core.llm import llm
from core.state import AgentState

from .prompts import COMPILER_PROMPT


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"```(?:json)?\s*", "", text).strip()
    return json.loads(text)


def compiler_node(state: AgentState):
    """
    Узел графа для компиляции итогового досье.
    """
    print("--- COMPILING ---")
    transcript = "\n".join([f"{m.type}: {m.content}" for m in state["messages"]])

    prompt = ChatPromptTemplate.from_template(COMPILER_PROMPT)

    chain_input = {"transcript": transcript, "research": state["research_results"]}

    rendered = prompt.format(**chain_input)
    print(f"--- COMPILER PROMPT ({len(rendered)} chars) ---")
    print(rendered[:800])
    print("--- COMPILER PROMPT END ---")

    chain = prompt | llm
    result = chain.invoke(chain_input)

    print(f"--- COMPILER RAW ({len(result.content)} chars) ---")
    print(result.content[:500])
    print("--- COMPILER RAW END ---")

    raw = _parse_json(result.content)
    case_title = raw.get("title") or raw.get("case_title", "")
    case_summary = raw.get("summary") or raw.get("case_summary", "")
    case_file = raw.get("case_file") or raw.get("case_file_markdown", "")

    print(
        f"--- COMPILER PARSED: title={case_title[:60] if case_title else '(empty)'}, summary={case_summary[:60] if case_summary else '(empty)'}, case_file={len(case_file)} chars ---"
    )
    return {"case_file": case_file, "case_title": case_title, "case_summary": case_summary}
