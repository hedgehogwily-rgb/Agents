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
    "Посчитай 15 + 27 через calculator",
    "Прочитай файл examples/notes.txt и кратко скажи, о чём он",
    "Найди в examples/notes.txt строки про LangGraph через text_search",
    "Найди в examples/notes.txt строку со словом arithmetic через text_search, затем посчитай 15 + 27 через calculator и ответь обоими результатами",
]


def run_goal(graph, goal: str, max_steps: int = DEFAULT_MAX_STEPS) -> dict:
    return graph.invoke(
        {
            "goal": goal,
            "messages": [],
            "current_step": 0,
            "max_steps": max_steps,
            "final_answer": None,
            "last_tool_name": None,
            "last_observation": None,
            "plan": None,
            "trace": [],
        }
    )


def main() -> None:
    graph = build_graph()

    for goal in SAMPLE_GOALS:
        result = run_goal(graph, goal)
        logger.info("%s", goal)
        logger.info("%s/%s", result["current_step"], result["max_steps"])
        logger.info("%s", result.get("last_tool_name"))
        logger.info("%s", result.get("last_observation"))
        logger.info("%s", result["final_answer"])
        logger.info("%s", result["plan"])
        for step in result["trace"]:
            logger.info("%s", step)


if __name__ == "__main__":
    main()
