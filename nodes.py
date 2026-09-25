"""Graph node functions."""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

import prompts
from schemas import AgentState
from settings import get_llm
from tools import TOOLS, ToolObservation

logger = logging.getLogger(__name__)


def _llm_with_tools():
    return get_llm().bind_tools(TOOLS, parallel_tool_calls=False)


def actor_node(state: AgentState) -> dict:
    system = SystemMessage(content=prompts.ACTOR_SYSTEM.format(
        plan=state["plan"],
        last_observation=state["last_observation"],
    ))

    response = _llm_with_tools().invoke([system, *state["messages"]])

    if response.tool_calls:
        action = "; ".join(
            f"{call['name']} {call['args']}" for call in response.tool_calls
        )
    else:
        content = response.content
        action = content.strip() if isinstance(content, str) else str(content)
        
    update = {
        "messages": [response],
        "current_step": state["current_step"] + 1,
        "trace": state["trace"] + [f"action: {action}"],
    }

    if not getattr(response, "tool_calls", None):
        content = response.content
        if not isinstance(content, str):
            content = str(content)
        update["final_answer"] = content.strip()

    return update


def observe_node(state: AgentState) -> dict:
    """Pull new ToolMessages into state as observations (back into the graph)."""
    messages = state["messages"]
    last_ai_index = None
    for index, message in enumerate(messages):
        if isinstance(message, AIMessage):
            last_ai_index = index
    if last_ai_index is None:
        return {}

    tool_messages = [
        message
        for message in messages[last_ai_index + 1 :]
        if isinstance(message, ToolMessage)
    ]
    if not tool_messages:
        return {}

    trace = list(state["trace"])
    parsed = None
    for message in tool_messages:
        content = message.content if isinstance(message.content, str) else str(message.content)
        parsed = ToolObservation.model_validate_json(content)
        trace.append(f"observation: {parsed.tool_name}: {parsed.result}")

    return {
        "last_tool_name": parsed.tool_name,
        "last_observation": parsed.model_dump_json(),
        "trace": trace,
    }


def should_continue(state: AgentState) -> str:
    """Route: call tools, stop on step limit, or finish."""
    if state["current_step"] >= state["max_steps"]:
        return "end"

    last = state["messages"][-1] if state["messages"] else None
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return "end"


def planner_node(state: AgentState) -> dict:
    response = get_llm().invoke([
        SystemMessage(content=prompts.PLANNER_SYSTEM),
        HumanMessage(content=state["goal"]),
    ])
    plan_content = response.content
    plan = plan_content.strip() if isinstance(plan_content, str) else str(plan_content).strip()
    return {
        "plan": plan,
        "messages": [HumanMessage(content=state["goal"])],
        "trace": [f"plan: {plan}"],
    }