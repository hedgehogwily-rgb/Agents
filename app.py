"""HTTP entrypoint for the graph agent."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from pydantic import BaseModel, Field

from graph import build_graph
from main import GUARDRAIL_CASES, SAMPLE_GOALS, run_goal
from schemas import StopReason
from settings import DEFAULT_MAX_STEPS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(title="Agents", version="1.0.0")
graph = build_graph()


class TaskRequest(BaseModel):
    goal: str = Field(min_length=1)
    max_steps: int = Field(default=DEFAULT_MAX_STEPS, ge=1, le=20)


class GuardrailDemo(BaseModel):
    goal: str
    max_steps: int


class TaskResponse(BaseModel):
    goal: str
    final_answer: str | None
    stop_reason: str | None
    plan: str | None
    current_step: int
    max_steps: int
    done_criteria: list[str]
    observations: list[str]
    tool_results: list[str]
    trace: list[str]


def _stop_reason(value: StopReason | None) -> str | None:
    if value is None:
        return None
    return value.value


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/demos")
def demos() -> dict[str, list]:
    return {
        "goals": SAMPLE_GOALS,
        "guardrails": [
            GuardrailDemo(goal=goal, max_steps=max_steps).model_dump()
            for goal, max_steps in GUARDRAIL_CASES
        ],
    }


@app.post("/tasks", response_model=TaskResponse)
def run_task(body: TaskRequest) -> TaskResponse:
    result = run_goal(graph, body.goal, max_steps=body.max_steps)
    return TaskResponse(
        goal=body.goal,
        final_answer=result["final_answer"],
        stop_reason=_stop_reason(result["stop_reason"]),
        plan=result["plan"],
        current_step=result["current_step"],
        max_steps=result["max_steps"],
        done_criteria=result["done_criteria"],
        observations=result["observations"],
        tool_results=result["tool_results"],
        trace=result["trace"],
    )
