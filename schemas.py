from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from enum import Enum

class StopReason(Enum):
    FINAL_ANSWER = "final_answer"
    MAX_STEPS = "max_steps"
    TOOL_ERROR = "tool_error"
    NO_PROGRESS = "no_progress"
    

class AgentState(TypedDict):
    """Central graph state passed between nodes."""

    goal: str
    messages: Annotated[list[BaseMessage], add_messages]
    current_step: int
    max_steps: int
    final_answer: str | None
    last_tool_name: str | None
    last_observation: str | None
    plan: str | None
    trace: list[str]
    observations: list[str]
    tool_results: list[str]
    notes: list[str]
    done_criteria: list[str]
    stop_reason: StopReason | None



