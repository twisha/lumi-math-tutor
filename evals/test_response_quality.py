"""
Response quality tests for Lumi.

  test_no_spoiler   — LLM-as-judge: Lumi must not reveal the answer on first turn
  test_response_length — heuristic: ≤ 3 sentence-ending punctuation marks
  test_guardrail_redirect — out-of-scope topics get a warm redirect to math
  test_in_scope_no_redirect — in-scope topics are engaged with, not redirected

Run from project root:  pytest evals/test_response_quality.py -v
"""
import pytest
from evals.dataset import NO_SPOILER_CASES, GUARDRAIL_CASES
from evals.evaluators import no_spoiler, response_length, redirects_to_math
from core.tutor_brain import ask_lumi


@pytest.mark.parametrize(
    "description, user_input, grade, answer",
    NO_SPOILER_CASES,
    ids=[c[0] for c in NO_SPOILER_CASES],
)
def test_no_spoiler(description, user_input, grade, answer):
    reply, _, _ = ask_lumi(user_input, grade_group=grade)
    result = no_spoiler(user_input, reply, answer)
    assert result["score"] == 1, (
        f"\n  Spoiler detected: {result['reason']}"
        f"\n  Reply: {reply!r}"
    )


@pytest.mark.parametrize(
    "description, user_input, grade, answer",
    NO_SPOILER_CASES,
    ids=[c[0] for c in NO_SPOILER_CASES],
)
def test_response_length(description, user_input, grade, answer):
    reply, _, _ = ask_lumi(user_input, grade_group=grade)
    result = response_length(reply)
    assert result["score"] == 1, (
        f"\n  {result['reason']}"
        f"\n  Reply: {reply!r}"
    )


@pytest.mark.parametrize(
    "description, user_input, grade, should_redirect",
    [c for c in GUARDRAIL_CASES if c[3]],
    ids=[c[0] for c in GUARDRAIL_CASES if c[3]],
)
def test_guardrail_redirect(description, user_input, grade, should_redirect):
    reply, _, _ = ask_lumi(user_input, grade_group=grade)
    result = redirects_to_math(reply)
    assert result["score"] == 1, (
        f"\n  Expected redirect to math but got: {reply!r}"
    )


@pytest.mark.parametrize(
    "description, user_input, grade, should_redirect",
    [c for c in GUARDRAIL_CASES if not c[3]],
    ids=[c[0] for c in GUARDRAIL_CASES if not c[3]],
)
def test_in_scope_no_redirect(description, user_input, grade, should_redirect):
    """In-scope math should engage the child, not push them away."""
    reply, tool_log, _ = ask_lumi(user_input, grade_group=grade)
    tools_used = {entry["tool"] for entry in tool_log}
    assert "calculate" in tools_used or "check_answer" in tools_used, (
        f"\n  Expected Lumi to engage with in-scope math but got: {reply!r}"
        f"\n  Tools used: {tools_used}"
    )
