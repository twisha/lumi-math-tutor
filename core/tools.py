import ast
import json
import operator
import random

# ── Safe math evaluator ───────────────────────────────────────────────────────

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
}

def _safe_eval(expr: str) -> int:
    def _eval(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
        raise ValueError(f"Unsupported expression: {ast.dump(node)}")
    return _eval(ast.parse(expr, mode="eval").body)

# ── Topic / grade keywords ────────────────────────────────────────────────────

_MATH_KEYWORDS = {
    "number", "count", "add", "plus", "subtract", "minus", "equals",
    "how many", "total", "more", "less", "sum", "difference",
    "zero", "one", "two", "three", "four", "five", "six", "seven",
    "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
    "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
}

_OUT_OF_SCOPE_KEYWORDS = {
    "multiply", "multiplication", "times", "divide", "division",
    "fraction", "decimal", "algebra", "variable", "equation",
    "percentage", "percent", "square root", "exponent", "power",
    "geometry", "calculus", "trigonometry",
}

_TOPIC_CATEGORIES = {
    "food": {"pizza", "burger", "candy", "cake", "food", "eat", "hungry", "lunch", "snack", "cookie", "ice cream"},
    "animals": {"dog", "cat", "bird", "fish", "animal", "pet", "horse", "rabbit", "lion", "tiger", "bear"},
    "entertainment": {"game", "play", "movie", "tv", "show", "youtube", "roblox", "minecraft", "fortnite", "video"},
    "personal": {"love", "like", "friend", "family", "mom", "dad", "sister", "brother", "school", "teacher"},
}

# ── Tool implementations ──────────────────────────────────────────────────────

def calculate(expression: str) -> dict:
    try:
        result = _safe_eval(expression)
        return {"result": result, "expression": expression}
    except Exception as e:
        return {"error": str(e), "expression": expression}


def check_answer(expected: int | float, given: int | float) -> dict:
    correct = int(expected) == int(given)
    return {"correct": correct, "expected": int(expected), "given": int(given)}


def generate_problem(operation: str = "addition", max_number: int = 10) -> dict:
    max_number = min(max_number, 20)
    if operation == "subtraction":
        a = random.randint(1, max_number)
        b = random.randint(0, a)
        problem = f"What is {a} minus {b}?"
        answer = a - b
    else:
        a = random.randint(0, max_number)
        b = random.randint(0, max_number - a)
        problem = f"What is {a} plus {b}?"
        answer = a + b
    return {"problem": problem, "operation": operation, "answer": answer}


def check_topic(text: str) -> dict:
    lower = text.lower()
    if any(kw in lower for kw in _MATH_KEYWORDS) or any(ch.isdigit() for ch in text):
        return {"is_math": True, "category": "math"}
    for category, keywords in _TOPIC_CATEGORIES.items():
        if any(kw in lower for kw in keywords):
            return {"is_math": False, "category": category}
    return {"is_math": False, "category": "unclear"}


def check_grade_level(topic: str) -> dict:
    lower = topic.lower()
    in_scope = not any(kw in lower for kw in _OUT_OF_SCOPE_KEYWORDS)
    return {"in_scope": in_scope, "topic": topic}


# ── Tool registry ─────────────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Safely evaluate a simple arithmetic expression and return the result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "A simple math expression, e.g. '3 + 5' or '10 - 4'."
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_answer",
            "description": "Check whether a child's numerical answer matches the expected answer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expected": {"type": "number", "description": "The correct answer."},
                    "given":    {"type": "number", "description": "The child's answer."}
                },
                "required": ["expected", "given"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_problem",
            "description": "Generate a random K-2 math problem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation":  {
                        "type": "string",
                        "enum": ["addition", "subtraction"],
                        "description": "The type of operation."
                    },
                    "max_number": {
                        "type": "integer",
                        "description": "Largest number to use (max 20)."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_topic",
            "description": "Check whether the child's input is math-related or off-topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The child's input text."}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_grade_level",
            "description": "Check whether a math topic is within K-2 scope.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "The math topic or question."}
                },
                "required": ["topic"]
            }
        }
    },
]

_TOOL_FN_MAP = {
    "calculate":        calculate,
    "check_answer":     check_answer,
    "generate_problem": generate_problem,
    "check_topic":      check_topic,
    "check_grade_level": check_grade_level,
}


def execute_tool(name: str, args: dict) -> str:
    fn = _TOOL_FN_MAP.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    return json.dumps(fn(**args))
