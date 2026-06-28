import os
from unittest.mock import MagicMock, patch

import pytest

from modules.research.node import analyze_case_intake, perform_legal_research, research_node


class TestResearchNode:
    def test_research_node_returns_research_results(self, agent_state):
        """research_node возвращает ключ research_results с непустой строкой."""
        result = research_node(agent_state)
        assert "research_results" in result
        assert len(result["research_results"]) > 0

    def test_research_node_includes_summary(self, agent_state):
        """research_results содержит информацию по делу."""
        result = research_node(agent_state)
        assert "TAVILY_DISABLED" in result["research_results"]

    def test_research_node_with_empty_messages(self):
        """Пустой список сообщений — всё равно работает."""
        result = research_node(
            {
                "messages": [],
                "case_id": "test",
            }
        )
        assert "research_results" in result

    def test_research_node_builds_transcript(self, agent_state):
        """Транскрипт строится из всех сообщений."""
        result = research_node(agent_state)
        # research_results должен содержать результат от LLM (то, что вернул мок)
        assert result["research_results"]


class TestPerformLegalResearch:
    def test_tavily_disabled(self):
        """TAVILY_DISABLED=true → поиск пропускается."""
        result = perform_legal_research("some query")
        assert "TAVILY_DISABLED" in result

    def test_no_api_key(self, monkeypatch):
        """Нет ключа → сообщение об ошибке."""
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.setenv("TAVILY_DISABLED", "")
        result = perform_legal_research("query")
        assert "TAVILY_API_KEY" in result

    @pytest.mark.skipif(not os.getenv("TAVILY_API_KEY"), reason="TAVILY_API_KEY не задан")
    def test_tavily_success_live(self, monkeypatch):
        """Реальный Tavily-поиск (только если ключ есть)."""
        monkeypatch.setenv("TAVILY_DISABLED", "")
        result = perform_legal_research("кража телефона УК РФ статья 158")
        assert "ошибк" not in result.lower()
        assert len(result) > 50

    @patch("modules.research.node.TavilySearchResults")
    def test_tavily_search_error_handled(self, mock_tavily, monkeypatch):
        """Tavily упал — возвращаем сообщение об ошибке, не исключение."""
        monkeypatch.setenv("TAVILY_DISABLED", "")
        monkeypatch.setenv("TAVILY_API_KEY", "test-key")
        mock_instance = MagicMock()
        mock_instance.invoke.side_effect = Exception("Tavily timeout")
        mock_tavily.return_value = mock_instance

        result = perform_legal_research("query")
        assert "ошибк" in result.lower()
        assert "Tavily timeout" in result


class TestAnalyzeCaseIntake:
    def test_analyze_returns_query(self, transcript):
        """analyze_case_intake возвращает непустой поисковый запрос."""
        query = analyze_case_intake(transcript)
        assert isinstance(query, str)
        assert len(query) > 0

    def test_analyze_with_empty_transcript(self):
        """Пустой транскрипт — всё равно что-то возвращаем."""
        query = analyze_case_intake("")
        assert isinstance(query, str)
