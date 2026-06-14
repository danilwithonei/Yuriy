import os
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from core.llm import llm
from core.state import AgentState
from .prompts import RESEARCHER_PROMPT, QUERY_ANALYZER_PROMPT

def analyze_case_intake(transcript: str) -> str:
    """
    Анализирует переписку для формирования поискового запроса.
    """
    prompt = ChatPromptTemplate.from_template(QUERY_ANALYZER_PROMPT)
    chain = prompt | llm
    query = chain.invoke({"transcript": transcript})
    return query.content

def perform_legal_research(query: str) -> str:
    """
    Выполняет поиск в интернете и синтезирует отчет.
    """
    if not os.getenv("TAVILY_API_KEY"):
        return "Ошибка: TAVILY_API_KEY не установлен. Исследование пропущено."

    search = TavilySearchResults(max_results=5)
    try:
        results = search.invoke(query)
    except Exception as e:
        return f"Ошибка при выполнении поиска: {str(e)}"
    
    prompt = ChatPromptTemplate.from_template(RESEARCHER_PROMPT)
    chain = prompt | llm
    summary = chain.invoke({"results": results})
    return summary.content

def research_node(state: AgentState):
    """
    Узел графа для проведения исследования.
    """
    print("--- RESEARCHING ---")
    transcript = "\n".join([f"{m.type}: {m.content}" for m in state["messages"]])
    query = analyze_case_intake(transcript)
    results = perform_legal_research(query)
    return {"research_results": results}
