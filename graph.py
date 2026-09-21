"""LangGraph assembly: linear Day-1 skeleton."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from nodes import propose_next_action
from schemas import AgentState


def build_graph():
    """Build and compile the minimal agent graph."""
    graph = StateGraph(AgentState)
    graph.add_node("propose_next_action", propose_next_action)
    graph.add_edge(START, "propose_next_action")
    graph.add_edge("propose_next_action", END)
    return graph.compile()
