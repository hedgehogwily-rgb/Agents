from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from nodes import planner_node, observe_node, should_continue, actor_node
from schemas import AgentState
from tools import TOOLS


def build_graph():
    """Build and compile the agent graph with tool calling."""
    graph = StateGraph(AgentState)
    graph.add_node("planner", planner_node)
    graph.add_node("actor", actor_node)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_node("state_updater", observe_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "actor")
    graph.add_conditional_edges(
        "actor",
        should_continue,
        {"tools": "tools", "end": END},
    )
    graph.add_edge("tools", "state_updater")
    graph.add_edge("state_updater", "actor")

    return graph.compile()
