import pytest

from modules.compiler.node import compiler_node


def test_compiler_returns_expected_keys(agent_state):
    """Базовый happy path: стандартные ключи title/summary/case_file."""
    result = compiler_node(agent_state)
    assert "case_title" in result
    assert "case_summary" in result
    assert "case_file" in result
    assert result["case_title"] == "Кража iPhone в кафе"
    assert result["case_summary"].startswith("Хищение телефона")
    assert result["case_file"].startswith("# Досье дела")


def test_compiler_case_title_fallback(agent_state):
    """Если LLM вернул case_title вместо title — fallback работает."""
    from langchain_core.messages import AIMessage

    import core.llm as llm_module

    raw = '{\n  "case_title": "Кража в кафе",\n  "case_summary": "Описание кражи.",\n  "case_file": "# Досье"\n}'
    object.__setattr__(llm_module.llm, "invoke", lambda m, c=None, **kw: AIMessage(content=raw))

    result = compiler_node(agent_state)
    assert result["case_title"] == "Кража в кафе"
    assert result["case_summary"] == "Описание кражи."
    assert result["case_file"] == "# Досье"


def test_compiler_title_field_wins_over_case_title(agent_state):
    """Если LLM вернул и title, и case_title — title приоритетнее."""
    from langchain_core.messages import AIMessage

    import core.llm as llm_module

    raw = (
        "{\n"
        '  "title": "Title побеждает",\n'
        '  "case_title": "Не должен использоваться",\n'
        '  "summary": "Описание",\n'
        '  "case_file": "# Досье"\n'
        "}"
    )
    object.__setattr__(llm_module.llm, "invoke", lambda m, c=None, **kw: AIMessage(content=raw))

    result = compiler_node(agent_state)
    assert result["case_title"] == "Title побеждает"


def test_compiler_malformed_json_raises(agent_state):
    """Битый JSON от LLM -> исключение -> catch в run_background_research."""
    from langchain_core.messages import AIMessage

    import core.llm as llm_module

    object.__setattr__(llm_module.llm, "invoke", lambda m, c=None, **kw: AIMessage(content="not json at all"))

    with pytest.raises(Exception):
        compiler_node(agent_state)


def test_compiler_empty_response_raises(agent_state):
    """Пустой ответ от LLM -> исключение."""
    from langchain_core.messages import AIMessage

    import core.llm as llm_module

    object.__setattr__(llm_module.llm, "invoke", lambda m, c=None, **kw: AIMessage(content=""))

    with pytest.raises(Exception):
        compiler_node(agent_state)


def test_compiler_json_in_code_block(agent_state):
    """LLM иногда оборачивает JSON в ```json … ``` — парсер должен снять."""
    from langchain_core.messages import AIMessage

    import core.llm as llm_module

    raw = (
        '```json\n{\n  "title": "Из code-блока",\n  "summary": "Из блока.",\n  "case_file": "# Досье из блока"\n}\n```'
    )
    object.__setattr__(llm_module.llm, "invoke", lambda m, c=None, **kw: AIMessage(content=raw))

    result = compiler_node(agent_state)
    assert result["case_title"] == "Из code-блока"
    assert result["case_file"] == "# Досье из блока"


def test_compiler_extra_fields_ignored(agent_state):
    """Лишние ключи от LLM не мешают."""
    from langchain_core.messages import AIMessage

    import core.llm as llm_module

    raw = (
        "{\n"
        '  "title": "Название",\n'
        '  "summary": "Описание.",\n'
        '  "case_file": "# Досье",\n'
        '  "extra_field": "не мешает",\n'
        '  "another": 123\n'
        "}"
    )
    object.__setattr__(llm_module.llm, "invoke", lambda m, c=None, **kw: AIMessage(content=raw))

    result = compiler_node(agent_state)
    assert result["case_title"] == "Название"
    assert result["case_file"] == "# Досье"


def test_compiler_all_fields_empty(agent_state):
    """LLM вернул пустые строки — всё равно возвращаем."""
    from langchain_core.messages import AIMessage

    import core.llm as llm_module

    raw = '{"title": "", "summary": "", "case_file": ""}'
    object.__setattr__(llm_module.llm, "invoke", lambda m, c=None, **kw: AIMessage(content=raw))

    result = compiler_node(agent_state)
    assert result["case_title"] == ""
    assert result["case_summary"] == ""
    assert result["case_file"] == ""


def test_compiler_missing_case_file_field(agent_state):
    """Если LLM не вернул case_file — возвращаем пустую строку."""
    from langchain_core.messages import AIMessage

    import core.llm as llm_module

    raw = '{"title": "Только название", "summary": "Только описание"}'
    object.__setattr__(llm_module.llm, "invoke", lambda m, c=None, **kw: AIMessage(content=raw))

    result = compiler_node(agent_state)
    assert result["case_title"] == "Только название"
    assert result["case_file"] == ""
