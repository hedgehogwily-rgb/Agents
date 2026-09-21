"""Graph node functions."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

import prompts
from schemas import AgentState
from settings import get_llm


def propose_next_action(state: AgentState) -> dict:
    """Read goal from state, ask the LLM for the next action, update state."""
    goal = state["goal"]
    llm = get_llm()

    human = HumanMessage(content=goal)
    response = llm.invoke(
        [
            SystemMessage(content=prompts.PROPOSE_NEXT_ACTION_SYSTEM),
            human,
        ]
    )
    action_text = response.content
    if not isinstance(action_text, str):
        action_text = str(action_text)

    return {
        "messages": [human, response],
        "current_step": state["current_step"] + 1,
        "final_answer": action_text.strip(),
    }
