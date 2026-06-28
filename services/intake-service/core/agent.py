from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import HumanMessage

from core.logger import logger
from graph import app_graph
from modules.compiler.node import compiler_node
from modules.research.node import research_node

# TODO: Known LangGraph issues:
# 1. run_background_research calls research_node + compiler_node directly (sync),
#    bypassing graph. Should use ainvoke or astream_events once LangGraph supports
#    streaming + background execution without graph state corruption.
# 2. astream_events version="v1" may need migration to "v2" in future LangGraph release.
# 3. Graph state access via thread_id is fragile — no lock on concurrent access.


class AgentService:
    @staticmethod
    async def handle_user_message_stream(case_id: str, message: str) -> AsyncGenerator[tuple[str, Any], None]:
        config = {"configurable": {"thread_id": str(case_id)}}

        current_state = app_graph.get_state(config)

        if current_state.next and "wait_for_input" in current_state.next:
            app_graph.update_state(config, {"messages": [HumanMessage(content=message)]}, as_node="wait_for_input")
            invoke_input = None
        else:
            invoke_input = {"messages": [HumanMessage(content=message)], "case_id": case_id}

        buffer = ""
        try:
            async for event in app_graph.astream_events(invoke_input, config=config, version="v1"):
                kind = event["event"]
                if kind == "on_chat_model_stream":
                    node = event.get("metadata", {}).get("langgraph_node", "")
                    if node == "intake":
                        content = event["data"]["chunk"].content
                        if content:
                            buffer += content
                            # Выплёвываем только законченные строки без [IS_READY:
                            while "\n" in buffer:
                                line, buffer = buffer.split("\n", 1)
                                if "[IS_READY:" not in line:
                                    yield ("token", line + "\n")
        except Exception as e:
            logger.error(f"Graph stream error for case_id={case_id}: {e}")
            raise
        else:
            if buffer and "[IS_READY:" not in buffer:
                yield ("token", buffer)

        final_state = app_graph.get_state(config)
        is_ready = bool(final_state.next and "research" in final_state.next)
        output = final_state.values
        yield ("result", (output, is_ready))

    @staticmethod
    async def confirm_and_resume(case_id: str) -> bool:
        config = {"configurable": {"thread_id": str(case_id)}}

        app_graph.update_state(config, {"is_confirmed": True})

        return True

    @staticmethod
    async def run_background_research(case_id: str) -> dict[str, Any]:
        config = {"configurable": {"thread_id": str(case_id)}}
        state = app_graph.get_state(config)
        current = dict(state.values)

        # На всякий случай проверяем, не запущен ли уже research через граф (ainvoke)
        if not current.get("research_results"):
            logger.info(f"Direct research call for case_id={case_id}: running research_node + compiler_node")
            try:
                research_out = research_node(current)
                current.update(research_out)
                app_graph.update_state(config, research_out)

                compiler_out = compiler_node(current)
                current.update(compiler_out)
                app_graph.update_state(config, compiler_out)
            except Exception as e:
                logger.error(f"Research/compiler failed for case_id={case_id}: {e}")
                return {}

        return {
            "case_file": current.get("case_file"),
            "case_title": current.get("case_title"),
            "case_summary": current.get("case_summary"),
            "research_results": current.get("research_results"),
        }
