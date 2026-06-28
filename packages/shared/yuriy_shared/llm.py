import os

from langchain_openai import ChatOpenAI


def get_llm(model_name: str | None = None):
    base_host = os.getenv(
        "DASHSCOPE_BASE_HOST",
        "ws-8xsmg0t4kftupsd5.ap-southeast-1.maas.aliyuncs.com",
    )
    return ChatOpenAI(
        model=model_name or os.getenv("LLM_MODEL", "qwen3.7-plus"),
        openai_api_key=os.getenv("DASHSCOPE_API_KEY"),
        openai_api_base=f"https://{base_host}/compatible-mode/v1",
        timeout=int(os.getenv("LLM_TIMEOUT", "300")),
    )


llm = get_llm()
