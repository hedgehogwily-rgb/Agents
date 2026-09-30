"""Graph node functions."""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from pydantic import ValidationError

import prompts
from schemas import AgentState, StopReason
from settings import get_llm
from langgraph.prebuilt import ToolNode

from tools import TOOLS, ToolObservation

logger = logging.getLogger(__name__)


def _node(name: str) -> str:
    logger.info("node: %s", name)
    return f"node: {name}"


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


def _parse_observation(message: ToolMessage, content: str) -> ToolObservation:
    try:
        return ToolObservation.model_validate_json(content)
    except ValidationError:
        text = content.strip()
        if not text.startswith("error"):
            text = f"error: {text}"
        return ToolObservation(
            tool_name=getattr(message, "name", None) or "unknown",
            result=text,
        )


def _no_progress(tool_results: list[str]) -> bool:
    if len(tool_results) < 2:
        return False
    prev, last = tool_results[-2], tool_results[-1]
    same_call = prev.split("=>", 1)[0] == last.split("=>", 1)[0]
    same_result = prev.split("=>", 1)[-1].strip() == last.split("=>", 1)[-1].strip()
    return same_call or same_result


def actor_node(state: AgentState) -> dict:
    if state["stop_reason"]:
        return {}

    if state["current_step"] >= state["max_steps"]:
        return {
            "stop_reason": StopReason.MAX_STEPS,
            "final_answer": state["final_answer"] or "Остановлено: достигнут max_steps.",
            "trace": state["trace"] + [_node("actor"), "stop: max_steps"],
        }

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
            action = (
                "Остановлено: повтор шага без нового результата. "
                + " | ".join(state["notes"])
            )
            return {
                "messages": [AIMessage(content=action)],
                "current_step": state["current_step"] + 1,
                "final_answer": action,
                "stop_reason": StopReason.NO_PROGRESS,
                "trace": state["trace"] + [_node("actor"), f"action: {signature}", "stop: no_progress"],
            }
        action = signature
    else:
        content = response.content
        action = content.strip() if isinstance(content, str) else str(content)

    trace = state["trace"] + [_node("actor"), f"action: {action}"]
    update = {
        "messages": [response],
        "current_step": state["current_step"] + 1,
        "trace": trace,
    }

    if not getattr(response, "tool_calls", None):
        content = response.content
        if not isinstance(content, str):
            content = str(content)
        update["final_answer"] = content.strip()
        update["stop_reason"] = StopReason.FINAL_ANSWER
        update["trace"] = trace + ["stop: final_answer"]

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

    trace = list(state["trace"]) + [_node("state_updater")]
    parsed = None
    tool_results = list(state["tool_results"])
    observations = list(state["observations"])
    for message in tool_messages:
        content = message.content if isinstance(message.content, str) else str(message.content)
        parsed = _parse_observation(message, content)
        trace.append(f"observation: {parsed.tool_name}: {parsed.result}")

        args = {}
        if isinstance(messages[last_ai_index], AIMessage):
            calls = messages[last_ai_index].tool_calls
            if calls:
                args = calls[-1]["args"]
        short = parsed.result[:180]
        record = f"{parsed.tool_name} {args} => {short}"

        result_text = parsed.result.strip()
        failed = result_text.startswith("error")
        same_error = (
            failed
            and state["tool_results"]
            and state["tool_results"][-1].split("=>", 1)[-1].strip() == result_text[:180]
        )
        tool_results.append(record)
        observations.append(f"{parsed.tool_name}: {short}")
        tool_results = tool_results[-5:]
        observations = observations[-5:]

        if same_error:
            trace.append("stop: tool_error")
            return {
                "tool_results": tool_results,
                "observations": observations,
                "notes": tool_results[:],
                "last_tool_name": parsed.tool_name,
                "last_observation": parsed.model_dump_json(),
                "stop_reason": StopReason.TOOL_ERROR,
                "final_answer": f"Остановлено: повтор ошибки инструмента. {result_text}",
                "trace": trace,
            }

        if _no_progress(tool_results):
            trace.append("stop: no_progress")
            return {
                "tool_results": tool_results,
                "observations": observations,
                "notes": tool_results[:],
                "last_tool_name": parsed.tool_name,
                "last_observation": parsed.model_dump_json(),
                "stop_reason": StopReason.NO_PROGRESS,
                "final_answer": "Остановлено: повтор шага без нового результата.",
                "trace": trace,
            }

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


def tools_node(state: AgentState, config: RunnableConfig) -> dict:
    line = _node("tools")
    update = ToolNode(TOOLS).invoke(state, config)
    if not isinstance(update, dict):
        update = {"messages": update}
    update["trace"] = state["trace"] + [line]
    return update


def should_continue(state: AgentState) -> str:
    if state["stop_reason"]:
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
        "trace": [_node("planner"), f"plan: {plan}", f"done_criteria: {done_criteria}"],
        "done_criteria": done_criteria,
    }