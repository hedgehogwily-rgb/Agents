from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from nodes import agent_node, observe_node, should_continue
from schemas import AgentState
from tools import TOOLS


def build_graph():
    """Build and compile the agent graph with tool calling."""
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_node("observe", observe_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "end": END},
    )
    graph.add_edge("tools", "observe")
    graph.add_edge("observe", "agent")

    return graph.compile()
