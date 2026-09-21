"""Configuration loaded from environment / .env."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Optional LangSmith tracing (enable later with LANGCHAIN_TRACING_V2=true)
LANGCHAIN_TRACING_V2: str | None = os.getenv("LANGCHAIN_TRACING_V2")
LANGCHAIN_API_KEY: str | None = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "agents-day01")

DEFAULT_MAX_STEPS: int = int(os.getenv("DEFAULT_MAX_STEPS", "5"))


def get_llm():
    """Return a chat model configured from settings."""
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to .env before running the agent."
        )

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=OPENAI_MODEL,
        api_key=OPENAI_API_KEY,
        temperature=0,
    )
