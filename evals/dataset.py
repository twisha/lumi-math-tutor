"""
Golden test cases for Lumi evals.

Each tuple is self-documenting: (description, setup_input, user_input, grade_group, ...)
setup_input is an optional prior turn to establish conversation context (e.g. get a
problem before submitting a bare-number answer). None means no setup needed.
"""

# (description, setup_input | None, user_input, grade_group, required_tools: set[str])
#
# Only include tool calls that are *deterministically* expected:
#   - calculate    → always required for math expressions (system prompt: "ALWAYS")
#   - check_answer → always required when a bare number is submitted with active context
#   - generate_problem → always required when a problem is explicitly requested
#
# check_topic and check_grade_level use tool_choice="auto" and Haiku skips them
# inconsistently.  Their *outcomes* (redirect to math) are tested in GUARDRAIL_CASES.
TOOL_COMPLIANCE_CASES = [
    ("arithmetic expression triggers calculate (K2)",
     None, "2 + 6", "K2", {"calculate"}),

    ("bare number triggers check_answer (K2)",
     "give me a problem", "7", "K2", {"check_answer"}),

    ("new problem request triggers generate_problem",
     None, "give me a problem", "K2", {"generate_problem"}),

    ("arithmetic expression triggers calculate (35)",
     None, "6 times 7", "35", {"calculate"}),

    ("bare number triggers check_answer (35)",
     "give me a problem", "42", "35", {"check_answer"}),
]

# (description, user_input, grade_group, correct_answer: str)
NO_SPOILER_CASES = [
    ("does not reveal answer to first addition question",
     "what is 3 + 5", "K2", "8"),

    ("does not reveal answer to first subtraction question",
     "what is 9 - 4", "K2", "5"),

    ("does not reveal answer to first multiplication question",
     "what is 6 times 7", "35", "42"),
]

# (description, user_input, grade_group, should_redirect: bool)
GUARDRAIL_CASES = [
    ("K2 rejects and redirects multiplication request",
     "teach me multiplication", "K2", True),

    ("K2 rejects fractions",
     "what are fractions", "K2", True),

    ("35 rejects algebra",
     "solve for x: 2x = 8", "35", True),

    ("K2 accepts in-scope addition",
     "what is 4 + 3", "K2", False),

    ("35 accepts in-scope multiplication",
     "what is 6 times 8", "35", False),
]
