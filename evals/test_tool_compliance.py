"""
Deterministic tests: verify Lumi calls the correct tools for each input.

These make real API calls to Claude but are cheap (Haiku) and fast.
Run from the project root:  pytest evals/test_tool_compliance.py -v
"""
import pytest
from evals.dataset import TOOL_COMPLIANCE_CASES
from core.tutor_brain import ask_lumi


@pytest.mark.parametrize(
    "description, setup_input, user_input, grade, required_tools",
    TOOL_COMPLIANCE_CASES,
    ids=[c[0] for c in TOOL_COMPLIANCE_CASES],
)
def test_tool_compliance(description, setup_input, user_input, grade, required_tools):
    if setup_input:
        ask_lumi(setup_input, grade_group=grade)  # establish conversation context
    _, tool_log, _ = ask_lumi(user_input, grade_group=grade)
    tools_used = {entry["tool"] for entry in tool_log}
    assert required_tools.issubset(tools_used), (
        f"\n  Required : {required_tools}"
        f"\n  Got      : {tools_used}"
        f"\n  Input    : {user_input!r} (grade={grade})"
        + (f"\n  Setup    : {setup_input!r}" if setup_input else "")
    )
