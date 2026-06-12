import os
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from prompts import RESEARCHER_PROMPT, QUERY_ANALYZER_PROMPT

load_dotenv()

def perform_legal_research(query: str) -> str:
    """
    Performs web research on a given legal query and returns a summarized report.
    """
    if not os.getenv("TAVILY_API_KEY"):
        return "Ошибка: TAVILY_API_KEY не установлен. Исследование пропущено."

    search = TavilySearchResults(max_results=5)
    try:
        results = search.invoke(query)
    except Exception as e:
        return f"Ошибка при выполнении поиска: {str(e)}"
    
    llm = ChatOpenAI(
        model=os.getenv("LLM_MODEL", "qwen3.7-plus"),
        openai_api_key=os.getenv("DASHSCOPE_API_KEY"),
        openai_api_base="https://ws-8xsmg0t4kftupsd5.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
    )

    prompt = ChatPromptTemplate.from_template(RESEARCHER_PROMPT)
    
    chain = prompt | llm
    summary = chain.invoke({"results": results})
    return summary.content

def analyze_case_intake(transcript: str) -> str:
    """
    Analyzes the intake transcript to formulate a research query.
    """
    llm = ChatOpenAI(
        model=os.getenv("LLM_MODEL", "qwen3.7-plus"),
        openai_api_key=os.getenv("DASHSCOPE_API_KEY"),
        openai_api_base="https://ws-8xsmg0t4kftupsd5.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
    )

    prompt = ChatPromptTemplate.from_template(QUERY_ANALYZER_PROMPT)
    
    chain = prompt | llm
    query = chain.invoke({"transcript": transcript})
    return query.content
