"""
Patches core.mcp_bridge in sys.modules before tutor_brain imports it.

mcp_bridge spawns an MCP subprocess at import time. For evals we bypass it
by routing execute_tool directly to core.tools — same logic, no subprocess.

Import this module as the very first import in any eval entry point
(conftest.py and run_langsmith_evals.py both do this).
"""
import json
import sys
from unittest.mock import MagicMock

import core.tools as _tools

_FN_MAP = {
    "calculate":        _tools.calculate,
    "check_answer":     _tools.check_answer,
    "generate_problem": _tools.generate_problem,
    "check_topic":      _tools.check_topic,
    "check_grade_level": _tools.check_grade_level,
}

# Tool schemas mirrored from core/mcp_server.py
_TOOLS_ANTHROPIC = [
    {
        "name": "calculate",
        "description": "Safely evaluate a simple arithmetic expression and return the result.",
        "input_schema": {
            "type": "object",
            "properties": {"expression": {"type": "string", "description": "A simple math expression, e.g. '3 + 5'."}},
            "required": ["expression"],
        },
    },
    {
        "name": "check_answer",
        "description": "Check whether a child's numerical answer matches the expected answer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expected": {"type": "number", "description": "The correct answer."},
                "given":    {"type": "number", "description": "The child's answer."},
            },
            "required": ["expected", "given"],
        },
    },
    {
        "name": "generate_problem",
        "description": "Generate a random math problem appropriate for the current grade group.",
        "input_schema": {
            "type": "object",
            "properties": {
                "operation":   {"type": "string", "enum": ["addition", "subtraction", "multiplication", "division"]},
                "max_number":  {"type": "integer", "description": "Largest number to use (K-2 only, max 20)."},
                "grade_group": {"type": "string", "enum": ["K2", "35"]},
            },
            "required": [],
        },
    },
    {
        "name": "check_topic",
        "description": "Check whether the child's input is math-related or off-topic.",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "The child's input text."}},
            "required": ["text"],
        },
    },
    {
        "name": "check_grade_level",
        "description": "Check whether a math topic is within scope for the current grade group.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic":       {"type": "string", "description": "The math topic or question."},
                "grade_group": {"type": "string", "enum": ["K2", "35"]},
            },
            "required": ["topic"],
        },
    },
]


def _execute_tool(name: str, args: dict) -> str:
    fn = _FN_MAP.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    return json.dumps(fn(**args))


_bridge = MagicMock()
_bridge.TOOLS_ANTHROPIC = _TOOLS_ANTHROPIC
_bridge.execute_tool = _execute_tool

sys.modules["core.mcp_bridge"] = _bridge
