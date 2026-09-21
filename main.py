"""Day 1 entrypoint: run the graph on a few sample goals."""

from __future__ import annotations

import logging

from graph import build_graph
from settings import DEFAULT_MAX_STEPS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

SAMPLE_GOALS = [
    "Сложи 15 и 27",
    "Кратко объясни, что такое HTTP",
    "Составь план изучения Python за неделю",
]


def run_goal(graph, goal: str, max_steps: int = DEFAULT_MAX_STEPS) -> dict:
    return graph.invoke(
        {
            "goal": goal,
            "messages": [],
            "current_step": 0,
            "max_steps": max_steps,
            "final_answer": None,
        }
    )


def main() -> None:
    graph = build_graph()

    for goal in SAMPLE_GOALS:
        result = run_goal(graph, goal)
        logger.info("%s", goal)
        logger.info("%s/%s", result["current_step"], result["max_steps"])
        logger.info("%s", result["final_answer"])


if __name__ == "__main__":
    main()
