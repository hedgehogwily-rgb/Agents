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


def _call_signature(name: str, args: dict) -> str:
    return f"{name} {args}"


def _is_successful_repeat(signature: str, tool_results: list[str]) -> bool:
    prefix = signature + " =>"
    for record in tool_results:
        if not record.startswith(prefix):
            continue
        result = record.split("=>", 1)[1].strip()
        if not result.startswith("error"):
            return True
    return False


def actor_node(state: AgentState) -> dict:
    system = SystemMessage(content=prompts.ACTOR_SYSTEM.format(
        plan=state["plan"],
        last_observation=state["last_observation"],
        done_criteria=state["done_criteria"],
        notes=state["notes"],
        tool_results=state["tool_results"],
    ))

    response = _llm_with_tools().invoke([system, *state["messages"]])

    if response.tool_calls:
        call = response.tool_calls[0]
        signature = _call_signature(call["name"], call["args"])
        if _is_successful_repeat(signature, state["tool_results"]):
            response = AIMessage(
                content=(
                    "Этот вызов уже есть в notes. Ответь по сохранённым фактам: "
                    + " | ".join(state["notes"])
                )
            )
            action = response.content
        else:
            action = signature
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
    tool_results = list(state["tool_results"])
    observations = list(state["observations"])
    for message in tool_messages:
        content = message.content if isinstance(message.content, str) else str(message.content)
        parsed = ToolObservation.model_validate_json(content)
        trace.append(f"observation: {parsed.tool_name}: {parsed.result}")

        args = {}
        if isinstance(messages[last_ai_index], AIMessage):
            calls = messages[last_ai_index].tool_calls
            if calls:
                args = calls[-1]["args"]
        short = parsed.result[:180]
        record = f"{parsed.tool_name} {args} => {short}"

        tool_results.append(record)
        observations.append(f"{parsed.tool_name}: {short}")
    
    tool_results = tool_results[-5:]
    observations = observations[-5:]

    trace.append(
        f"state: tool_results={tool_results} notes={tool_results} done_criteria={state['done_criteria']}"
    )

    return {
        "tool_results": tool_results,
        "observations": observations,
        "notes": tool_results[:],
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

    response = get_llm().invoke([
        SystemMessage(content=prompts.DONE_CRITERIA_SYSTEM),
        HumanMessage(content=state["goal"]),
    ])
    done_criteria_content = response.content
    done_criteria = [
        line.strip(" -\t")
        for line in str(done_criteria_content).splitlines()
        if line.strip()
    ][:4]

    return {
        "plan": plan,
        "messages": [HumanMessage(content=state["goal"])],
        "trace": [f"plan: {plan}", f"done_criteria: {done_criteria}"],
        "done_criteria": done_criteria,
    }