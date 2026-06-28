import os
from contextlib import contextmanager
from typing import Any

import pytest
from langchain_core.messages import AIMessage

os.environ.setdefault("TAVILY_DISABLED", "true")
os.environ.setdefault("DASHSCOPE_API_KEY", "test-key")
os.environ.setdefault("LLM_TIMEOUT", "5")


DEFAULT_COMPILER_RESPONSE = (
    "{\n"
    '  "title": "Кража iPhone в кафе",\n'
    '  "summary": "Хищение телефона из общественного места, требуется адвокат.",\n'
    '  "case_file": "# Досье дела\\n\\n## Суть\\nКража.\\n\\n## Факты\\nТелефон пропал."\n'
    "}"
)


@pytest.fixture(autouse=True)
def mock_llm():
    """Подменяет llm.invoke через object.__setattr__ (ChatOpenAI — Pydantic v2, monkeypatch.setattr не работает)."""
    import core.llm as llm_module

    def fake_invoke(messages, config=None, **kwargs) -> AIMessage:
        return AIMessage(content=DEFAULT_COMPILER_RESPONSE)

    object.__setattr__(llm_module.llm, "invoke", fake_invoke)
    yield


@pytest.fixture
def change_llm_response():
    """Контекстный менеджер для временной смены ответа LLM.

    Использование:
        with change_llm_response('{"title": "test"}'):
            ...
    """
    import core.llm as llm_module

    @contextmanager
    def _change(raw: str):
        def fake_invoke(messages, config=None, **kwargs) -> AIMessage:
            return AIMessage(content=raw)

        object.__setattr__(llm_module.llm, "invoke", fake_invoke)
        yield

    return _change


@pytest.fixture
def transcript() -> str:
    return (
        "human: Здравствуйте! У меня украли телефон в кафе.\n"
        "ai: Понимаю. Расскажите подробнее, где и когда это произошло?\n"
        "human: Вчера вечером, на Невском проспекте.\n"
        "ai: Какая модель телефона и его стоимость?\n"
        "human: iPhone 15 Pro Max, 150 тысяч рублей.\n"
    )


@pytest.fixture
def research_results() -> str:
    return "Поиск по ключу отключён (TAVILY_DISABLED). Использую только знания модели."


@pytest.fixture
def agent_state(transcript: str, research_results: str) -> dict[str, Any]:
    from langchain_core.messages import AIMessage, HumanMessage

    return {
        "messages": [
            HumanMessage(content="Здравствуйте! У меня украли телефон."),
            AIMessage(content="Расскажите подробнее."),
            HumanMessage(content="iPhone 15 Pro Max, 150к."),
        ],
        "case_id": "test-uuid-1234",
        "is_ready": True,
        "is_confirmed": True,
        "research_results": research_results,
    }
