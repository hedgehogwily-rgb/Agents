from __future__ import annotations

import ast
import logging
import operator
from pathlib import Path

from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent
ALLOWED_ROOTS = (PROJECT_ROOT / "examples", PROJECT_ROOT)


# --- Pydantic input schemas -------------------------------------------------

class CalculatorInput(BaseModel):
    expression: str = Field(
        description="Арифметическое выражение, например '15 + 27' или '(2+3)*4'."
    )


class ReadLocalFileInput(BaseModel):
    path: str = Field(
        description="Путь к локальному текстовому файлу относительно проекта, "
        "например 'examples/notes.txt'."
    )


class TextSearchInput(BaseModel):
    path: str = Field(
        description="Путь к локальному текстовому файлу для поиска, "
        "например 'examples/notes.txt'."
    )
    query: str = Field(description="Подстрока для поиска (без regex).")


class ToolObservation(BaseModel):
    """Normalized tool output stored / logged as observation."""

    tool_name: str
    result: str


# --- helpers ----------------------------------------------------------------

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _eval_ast(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _BIN_OPS:
            raise ValueError(f"unsupported operator: {op_type.__name__}")
        return _BIN_OPS[op_type](_eval_ast(node.left), _eval_ast(node.right))
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _UNARY_OPS:
            raise ValueError(f"unsupported unary operator: {op_type.__name__}")
        return _UNARY_OPS[op_type](_eval_ast(node.operand))
    raise ValueError(f"unsupported expression node: {type(node).__name__}")


def _resolve_safe_path(path: str) -> Path:
    raw = Path(path)
    candidate = (PROJECT_ROOT / raw).resolve() if not raw.is_absolute() else raw.resolve()
    if not any(
        candidate == root.resolve() or root.resolve() in candidate.parents
        for root in ALLOWED_ROOTS
    ):
        raise ValueError(f"path outside allowed roots: {path}")
    if not candidate.is_file():
        raise FileNotFoundError(f"file not found: {path}")
    return candidate


def _log_tool(name: str, payload: dict, result: str) -> str:
    observation = ToolObservation(tool_name=name, result=result)
    serialized = observation.model_dump_json()
    logger.info("%s %s", name, payload)
    logger.info("%s %s", name, serialized)
    return serialized


# --- tools ------------------------------------------------------------------

@tool("calculator", args_schema=CalculatorInput)
def calculator(expression: str) -> str:
    """Вычисляет простое арифметическое выражение и возвращает число как строку."""
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        value = _eval_ast(tree)
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        result = str(value)
    except Exception as exc:  # noqa: BLE001 — observation must return error text
        result = f"error: {exc}"
    return _log_tool("calculator", {"expression": expression}, result)


@tool("read_local_file", args_schema=ReadLocalFileInput)
def read_local_file(path: str) -> str:
    """Читает содержимое локального текстового файла внутри проекта."""
    try:
        text = _resolve_safe_path(path).read_text(encoding="utf-8")
        result = text if text.strip() else "(empty file)"
    except Exception as exc:  # noqa: BLE001
        result = f"error: {exc}"
    return _log_tool("read_local_file", {"path": path}, result)


@tool("text_search", args_schema=TextSearchInput)
def text_search(path: str, query: str) -> str:
    """Ищет подстроку query в локальном файле и возвращает совпавшие строки."""
    try:
        lines = _resolve_safe_path(path).read_text(encoding="utf-8").splitlines()
        hits = [
            f"{idx}: {line}"
            for idx, line in enumerate(lines, start=1)
            if query.lower() in line.lower()
        ]
        result = "\n".join(hits) if hits else f"no matches for {query!r}"
    except Exception as exc:  # noqa: BLE001
        result = f"error: {exc}"
    return _log_tool("text_search", {"path": path, "query": query}, result)


TOOLS = [calculator, read_local_file, text_search]
TOOL_BY_NAME = {t.name: t for t in TOOLS}
