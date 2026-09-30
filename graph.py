from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from nodes import actor_node, observe_node, planner_node, should_continue, tools_node
from schemas import AgentState


def build_graph():
    """Build and compile the agent graph with tool calling."""
    graph = StateGraph(AgentState)
    graph.add_node("planner", planner_node)
    graph.add_node("actor", actor_node)
    graph.add_node("tools", tools_node)
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
