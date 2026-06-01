"""
MCP ↔ Anthropic tool format bridge.

Tool schemas are sourced from mcp_server.py (single source of truth).
Tool execution calls tools.py directly — this avoids async/threading
incompatibilities between anyio, nest_asyncio (installed by Chainlit),
and background event loops, while preserving the MCP architecture.
"""
import json

from core.tools import (
    calculate,
    check_answer,
    generate_problem,
    check_topic,
    check_grade_level,
)

# ── Tool schemas (Anthropic format) ──────────────────────────────────────────
# Kept in sync with mcp_server.py which is the canonical MCP definition.

TOOLS_ANTHROPIC: list[dict] = [
    {
        "name": "calculate",
        "description": "Safely evaluate a simple arithmetic expression and return the result.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A simple math expression, e.g. '3 + 5' or '10 - 4'."
                }
            },
            "required": ["expression"]
        }
    },
    {
        "name": "check_answer",
        "description": "Check whether a child's numerical answer matches the expected answer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expected": {"type": "number", "description": "The correct answer."},
                "given":    {"type": "number", "description": "The child's answer."}
            },
            "required": ["expected", "given"]
        }
    },
    {
        "name": "generate_problem",
        "description": "Generate a random K-2 math problem.",
        "input_schema": {
            "type": "object",
            "properties": {
                "operation":  {"type": "string", "enum": ["addition", "subtraction"]},
                "max_number": {"type": "integer", "description": "Largest number to use (max 20)."}
            },
            "required": []
        }
    },
    {
        "name": "check_topic",
        "description": "Check whether the child's input is math-related or off-topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The child's input text."}
            },
            "required": ["text"]
        }
    },
    {
        "name": "check_grade_level",
        "description": "Check whether a math topic is within K-2 scope.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "The math topic or question."}
            },
            "required": ["topic"]
        }
    },
]

# ── Tool execution (direct Python calls) ──────────────────────────────────────

_FN_MAP = {
    "calculate":         calculate,
    "check_answer":      check_answer,
    "generate_problem":  generate_problem,
    "check_topic":       check_topic,
    "check_grade_level": check_grade_level,
}


def execute_tool(name: str, args: dict) -> str:
    fn = _FN_MAP.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        return json.dumps(fn(**args))
    except TypeError as e:
        return json.dumps({"error": f"Invalid arguments: {e}"})
