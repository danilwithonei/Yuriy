import pytest
from unittest.mock import MagicMock, ANY
from core.agent import AgentService

pytestmark = pytest.mark.asyncio

CASE_ID = "test-uuid-1234"
FAKE_CONFIG = {"configurable": {"thread_id": CASE_ID}}


def _make_snapshot(values: dict, next_nodes: tuple[str, ...] = ()):
    """Создаёт имитацию StateSnapshot."""
    snap = MagicMock()
    snap.values = values
    snap.next = next_nodes
    return snap


class TestRunBackgroundResearch:
    @staticmethod
    def _make_state(**overrides) -> dict:
        """Базовая состоянии без research_results (чтобы не было short-circuit)."""
        from langchain_core.messages import HumanMessage, AIMessage
        state = {
            "messages": [
                HumanMessage(content="Здравствуйте! У меня украли телефон."),
                AIMessage(content="Расскажите подробнее."),
                HumanMessage(content="iPhone 15 Pro Max, 150к."),
            ],
            "case_id": CASE_ID,
            "is_ready": True,
            "is_confirmed": True,
        }
        state.update(overrides)
        return state

    async def test_full_flow_returns_structured_output(self, monkeypatch):
        """Полный цикл research → compiler → structured output."""
        state = self._make_state()
        mock_graph = MagicMock()
        mock_graph.get_state.return_value = _make_snapshot(state)
        monkeypatch.setattr("core.agent.app_graph", mock_graph)

        result = await AgentService.run_background_research(CASE_ID)

        assert result["case_file"] is not None
        assert result["case_title"] == "Кража iPhone в кафе"
        assert result["case_summary"] is not None
        assert result["research_results"] is not None

    async def test_skips_if_already_has_results(self, monkeypatch):
        """Если research_results уже есть — не запускаем research/compiler."""
        state = {"research_results": "already done"}
        mock_graph = MagicMock()
        mock_graph.get_state.return_value = _make_snapshot(state)
        monkeypatch.setattr("core.agent.app_graph", mock_graph)

        result = await AgentService.run_background_research(CASE_ID)

        # research_node не вызывался
        assert result["research_results"] == "already done"
        # compiler не вызывался → case_file None
        assert result["case_file"] is None

    async def test_exception_in_research_returns_empty(self, monkeypatch):
        """Ошибка в research_node → возвращаем {}."""
        import core.agent as agent_module
        mock_research = MagicMock(side_effect=RuntimeError("Tavily crashed"))
        monkeypatch.setattr(agent_module, "research_node", mock_research)

        state = self._make_state()
        mock_graph = MagicMock()
        mock_graph.get_state.return_value = _make_snapshot(state)
        monkeypatch.setattr("core.agent.app_graph", mock_graph)

        result = await AgentService.run_background_research(CASE_ID)

        assert result == {}

    async def test_exception_in_compiler_returns_empty(self, monkeypatch):
        """Ошибка в compiler_node → возвращаем {}."""
        import core.agent as agent_module
        import modules.research.node as research_module

        # research_node возвращает успех
        monkeypatch.setattr(
            research_module, "research_node",
            lambda s: {"research_results": "some results"},
        )
        # compiler_node падает
        mock_compiler = MagicMock(side_effect=ValueError("JSON parse error"))
        monkeypatch.setattr(agent_module, "compiler_node", mock_compiler)

        state = self._make_state()
        mock_graph = MagicMock()
        mock_graph.get_state.return_value = _make_snapshot(state)
        monkeypatch.setattr("core.agent.app_graph", mock_graph)

        result = await AgentService.run_background_research(CASE_ID)

        assert result == {}

    async def test_state_empty_messages(self, monkeypatch):
        """Пустой state (нет messages) — research/compiler должны упасть с KeyError."""
        state = {"case_id": CASE_ID}  # нет messages
        mock_graph = MagicMock()
        mock_graph.get_state.return_value = _make_snapshot(state)
        monkeypatch.setattr("core.agent.app_graph", mock_graph)

        result = await AgentService.run_background_research(CASE_ID)

        assert result == {}

    async def test_calls_update_state(self, monkeypatch):
        """update_state вызывается после research и после compiler."""
        state = self._make_state()
        mock_graph = MagicMock()
        mock_graph.get_state.return_value = _make_snapshot(state)
        monkeypatch.setattr("core.agent.app_graph", mock_graph)

        await AgentService.run_background_research(CASE_ID)

        # update_state должен быть вызван дважды (research + compiler)
        assert mock_graph.update_state.call_count == 2
        # Первый вызов — research_out (есть research_results)
        first_call = mock_graph.update_state.call_args_list[0]
        assert "research_results" in first_call[0][1]
        # Второй вызов — compiler_out (есть case_file)
        second_call = mock_graph.update_state.call_args_list[1]
        assert "case_file" in second_call[0][1]

    async def test_get_state_called_with_correct_config(self, monkeypatch):
        """get_state вызывается с thread_id=case_id."""
        state = self._make_state()
        mock_graph = MagicMock()
        mock_graph.get_state.return_value = _make_snapshot(state)
        monkeypatch.setattr("core.agent.app_graph", mock_graph)

        await AgentService.run_background_research(CASE_ID)

        config_arg = mock_graph.get_state.call_args[0][0]
        assert config_arg["configurable"]["thread_id"] == CASE_ID
