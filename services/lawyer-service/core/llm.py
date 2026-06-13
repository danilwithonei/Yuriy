import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

def get_llm(model_name: str = None):
    """
    Возвращает настроенный экземпляр ChatOpenAI для работы с Qwen через DashScope.
    """
    return ChatOpenAI(
        model=model_name or os.getenv("LLM_MODEL", "qwen3.7-plus"),
        openai_api_key=os.getenv("DASHSCOPE_API_KEY"),
        openai_api_base="https://ws-8xsmg0t4kftupsd5.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
    )

# Дефолтный экземпляр для переиспользования
llm = get_llm()
