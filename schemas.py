from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Central graph state passed between nodes."""

    goal: str
    messages: Annotated[list[BaseMessage], add_messages]
    current_step: int
    max_steps: int
    final_answer: str | None
    last_tool_name: str | None
    last_observation: str | None
