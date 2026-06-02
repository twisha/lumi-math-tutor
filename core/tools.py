import ast
import operator
import random

# ── Safe math evaluator ───────────────────────────────────────────────────────

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

def _safe_eval(expr: str) -> int | float:
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
    "how many", "total", "more", "less", "sum", "difference", "times",
    "multiply", "divide", "fraction", "half", "quarter",
    "zero", "one", "two", "three", "four", "five", "six", "seven",
    "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
    "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
}

_OUT_OF_SCOPE_K2 = {
    "multiply", "multiplication", "times", "divide", "division",
    "fraction", "decimal", "algebra", "variable", "equation",
    "percentage", "percent", "square root", "exponent", "power",
    "geometry", "calculus", "trigonometry",
}

_OUT_OF_SCOPE_35 = {
    "algebra", "variable", "equation", "calculus", "trigonometry",
    "percentage", "percent", "square root", "exponent", "power",
    "geometry formula", "pi ", "radius", "circumference", "derivative",
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
    correct = round(float(expected), 4) == round(float(given), 4)
    return {"correct": correct, "expected": expected, "given": given}


def generate_problem(operation: str = "addition", max_number: int = 10, grade_group: str = "K2") -> dict:
    if grade_group == "35":
        return _generate_35(operation)
    return _generate_k2(operation, max_number)


def _generate_k2(operation: str, max_number: int) -> dict:
    max_number = min(max_number, 20)
    if operation == "subtraction":
        a = random.randint(1, max_number)
        b = random.randint(0, a)
        return {"problem": f"What is {a} minus {b}?", "operation": operation, "answer": a - b}
    a = random.randint(0, max_number)
    b = random.randint(0, max_number - a)
    return {"problem": f"What is {a} plus {b}?", "operation": operation, "answer": a + b}


def _generate_35(operation: str) -> dict:
    if operation == "multiplication":
        a = random.randint(2, 12)
        b = random.randint(2, 12)
        return {"problem": f"What is {a} times {b}?", "operation": operation, "answer": a * b}
    if operation == "division":
        b = random.randint(2, 12)
        answer = random.randint(2, 12)
        a = b * answer
        return {"problem": f"What is {a} divided by {b}?", "operation": operation, "answer": answer}
    if operation == "subtraction":
        a = random.randint(50, 999)
        b = random.randint(10, a)
        return {"problem": f"What is {a} minus {b}?", "operation": operation, "answer": a - b}
    # default: addition
    a = random.randint(50, 500)
    b = random.randint(10, 500)
    return {"problem": f"What is {a} plus {b}?", "operation": operation, "answer": a + b}


def check_topic(text: str) -> dict:
    lower = text.lower()
    if any(kw in lower for kw in _MATH_KEYWORDS) or any(ch.isdigit() for ch in text):
        return {"is_math": True, "category": "math"}
    for category, keywords in _TOPIC_CATEGORIES.items():
        if any(kw in lower for kw in keywords):
            return {"is_math": False, "category": category}
    return {"is_math": False, "category": "unclear"}


def check_grade_level(topic: str, grade_group: str = "K2") -> dict:
    lower = topic.lower()
    out_of_scope = _OUT_OF_SCOPE_35 if grade_group == "35" else _OUT_OF_SCOPE_K2
    in_scope = not any(kw in lower for kw in out_of_scope)
    return {"in_scope": in_scope, "topic": topic, "grade_group": grade_group}
