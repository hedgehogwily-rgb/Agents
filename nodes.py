"""Graph node functions."""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

import prompts
from schemas import AgentState
from settings import get_llm
from tools import TOOLS

logger = logging.getLogger(__name__)


def _llm_with_tools():
    return get_llm().bind_tools(TOOLS)


def agent_node(state: AgentState) -> dict:
    """Call the LLM (with tools bound). May emit tool_calls or a final answer."""
    history = list(state["messages"])
    system = SystemMessage(content=prompts.AGENT_SYSTEM)

    if not history:
        human = HumanMessage(content=state["goal"])
        response = _llm_with_tools().invoke([system, human])
        update: dict = {
            "messages": [human, response],
            "current_step": state["current_step"] + 1,
        }
    else:
        response = _llm_with_tools().invoke([system, *history])
        update = {
            "messages": [response],
            "current_step": state["current_step"] + 1,
        }

    if not getattr(response, "tool_calls", None):
        content = response.content
        if not isinstance(content, str):
            content = str(content)
        update["final_answer"] = content.strip()

    return update


def observe_node(state: AgentState) -> dict:
    """Pull the latest ToolMessage into state as observation (back into the graph)."""
    tool_messages = [m for m in state["messages"] if isinstance(m, ToolMessage)]
    if not tool_messages:
        return {}

    last = tool_messages[-1]
    observation = last.content if isinstance(last.content, str) else str(last.content)
    tool_name = getattr(last, "name", None) or "unknown"

    logger.info("%s", tool_name)
    logger.info("%s", observation)

    return {
        "last_tool_name": tool_name,
        "last_observation": observation,
    }


def should_continue(state: AgentState) -> str:
    """Route: call tools, stop on step limit, or finish."""
    if state["current_step"] >= state["max_steps"]:
        return "end"

    last = state["messages"][-1] if state["messages"] else None
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return "end"
