import asyncio
from typing import Dict, Any, Tuple
from langchain_core.messages import HumanMessage
from graph import app_graph
from core.state import AgentState

class AgentService:
    @staticmethod
    async def handle_user_message(case_id: str, message: str) -> Tuple[Dict[str, Any], bool]:
        """
        Обрабатывает сообщение от пользователя, запуская или продолжая граф.
        Возвращает (output_state, is_ready).
        """
        config = {"configurable": {"thread_id": str(case_id)}}
        loop = asyncio.get_event_loop()
        
        # Проверяем текущее состояние графа
        current_state = await loop.run_in_executor(None, lambda: app_graph.get_state(config))
        
        if current_state.next and "wait_for_input" in current_state.next:
            # Если граф ждет ввода, обновляем состояние и продолжаем
            await loop.run_in_executor(None, lambda: app_graph.update_state(
                config, 
                {"messages": [HumanMessage(content=message)]},
                as_node="wait_for_input"
            ))
            output = await loop.run_in_executor(None, lambda: app_graph.invoke(None, config=config))
        else:
            # Если это начало или другое состояние
            input_state = {
                "messages": [HumanMessage(content=message)],
                "case_id": case_id
            }
            output = await loop.run_in_executor(None, lambda: app_graph.invoke(input_state, config=config))
            
        # Проверяем, остановился ли граф перед исследованием
        final_state = await loop.run_in_executor(None, lambda: app_graph.get_state(config))
        is_ready = final_state.next and "research" in final_state.next
        
        return output, is_ready

    @staticmethod
    async def confirm_and_resume(case_id: str) -> bool:
        """
        Устанавливает флаг подтверждения и запускает продолжение графа.
        """
        config = {"configurable": {"thread_id": str(case_id)}}
        loop = asyncio.get_event_loop()
        
        # Обновляем состояние флагом подтверждения
        await loop.run_in_executor(None, lambda: app_graph.update_state(
            config, 
            {"is_confirmed": True}
        ))
        
        # В основном процессе мы не вызываем invoke, так как исследование идет в фоне.
        # Этот метод просто подготавливает состояние.
        return True

    @staticmethod
    async def run_background_research(case_id: str) -> Dict[str, Any]:
        """
        Запускает выполнение графа с места прерывания (research).
        Используется в фоновых задачах.
        """
        config = {"configurable": {"thread_id": str(case_id)}}
        loop = asyncio.get_event_loop()
        
        # Продолжаем выполнение (исследование + компиляция)
        output = await loop.run_in_executor(None, lambda: app_graph.invoke(None, config=config))
        return output
