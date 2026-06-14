from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from core.state import AgentState
from modules.intake.node import intake_node
from modules.research.node import research_node
from modules.compiler.node import compiler_node

def wait_for_input(state: AgentState):
    """
    Узел-заглушка, на котором граф будет прерываться для ожидания сообщения от пользователя.
    """
    return {}

def should_continue(state: AgentState):
    """
    Маршрутизация: если ИИ готов — идем к исследованию, 
    если нет — идем ждать входные данные.
    """
    if state.get("is_ready", False):
        return "research"
    return "wait_for_input"

# Настройка графа
workflow = StateGraph(AgentState)

# Добавление узлов
workflow.add_node("intake", intake_node)
workflow.add_node("wait_for_input", wait_for_input)
workflow.add_node("research", research_node)
workflow.add_node("compiler", compiler_node)

# Определение связей
workflow.add_edge(START, "intake")
workflow.add_conditional_edges(
    "intake", 
    should_continue, 
    {
        "research": "research", 
        "wait_for_input": "wait_for_input"
    }
)

# Из ожидания ввода всегда возвращаемся в intake
workflow.add_edge("wait_for_input", "intake")

workflow.add_edge("research", "compiler")
workflow.add_edge("compiler", END)

# Компиляция: теперь прерываемся и перед исследованием, и перед ожиданием ввода
memory = MemorySaver()
app_graph = workflow.compile(
    checkpointer=memory, 
    interrupt_before=["research", "wait_for_input"]
)
