"""
MCP server that exposes Lumi's math tools over the stdio transport.
Run via: python -m core.mcp_server
"""
import asyncio
import json

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from core.tools import (
    calculate,
    check_answer,
    generate_problem,
    check_topic,
    check_grade_level,
)

app = Server("lumi-math-tools")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="calculate",
            description="Safely evaluate a simple arithmetic expression and return the result.",
            inputSchema={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "A simple math expression, e.g. '3 + 5' or '10 - 4'."
                    }
                },
                "required": ["expression"]
            }
        ),
        types.Tool(
            name="check_answer",
            description="Check whether a child's numerical answer matches the expected answer.",
            inputSchema={
                "type": "object",
                "properties": {
                    "expected": {"type": "number", "description": "The correct answer."},
                    "given":    {"type": "number", "description": "The child's answer."}
                },
                "required": ["expected", "given"]
            }
        ),
        types.Tool(
            name="generate_problem",
            description="Generate a random math problem appropriate for the current grade group.",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation":    {"type": "string", "enum": ["addition", "subtraction", "multiplication", "division"]},
                    "max_number":   {"type": "integer", "description": "Largest number to use (K-2 only, max 20)."},
                    "grade_group":  {"type": "string", "enum": ["K2", "35"], "description": "Grade group: K2 or 35."}
                },
                "required": []
            }
        ),
        types.Tool(
            name="check_topic",
            description="Check whether the child's input is math-related or off-topic.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The child's input text."}
                },
                "required": ["text"]
            }
        ),
        types.Tool(
            name="check_grade_level",
            description="Check whether a math topic is within scope for the current grade group.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic":       {"type": "string", "description": "The math topic or question."},
                    "grade_group": {"type": "string", "enum": ["K2", "35"], "description": "Grade group: K2 or 35."}
                },
                "required": ["topic"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    fn_map = {
        "calculate":         calculate,
        "check_answer":      check_answer,
        "generate_problem":  generate_problem,
        "check_topic":       check_topic,
        "check_grade_level": check_grade_level,
    }
    fn = fn_map.get(name)
    if fn is None:
        return [types.TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]
    try:
        return [types.TextContent(type="text", text=json.dumps(fn(**arguments)))]
    except TypeError as e:
        return [types.TextContent(type="text", text=json.dumps({"error": f"Invalid arguments: {e}"}))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
