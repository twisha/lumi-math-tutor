"""
Eval functions for Lumi.

Three kinds:
  - Deterministic: tools_called, response_length, redirects_to_math
  - LLM-as-judge:  no_spoiler  (calls Claude Haiku to check for answer leakage)

All functions return {"key": str, "score": 0|1, "reason": str}.
"""
import re
import anthropic

_judge = anthropic.Anthropic()
_JUDGE_MODEL = "claude-haiku-4-5-20251001"


# ── Deterministic evaluators ──────────────────────────────────────────────────

def tools_called(tool_log: list[dict], required: set[str]) -> dict:
    actual = {entry["tool"] for entry in tool_log}
    passed = required.issubset(actual)
    return {
        "key": "tool_compliance",
        "score": int(passed),
        "reason": f"required={required} actual={actual}",
    }


def response_length(reply: str, max_sentences: int = 3) -> dict:
    count = len(re.findall(r"[.!?]+", reply))
    passed = count <= max_sentences
    return {
        "key": "response_length",
        "score": int(passed),
        "reason": f"{count} sentence-ending marks (max {max_sentences})",
    }


def redirects_to_math(reply: str) -> dict:
    """Check that the reply steers the child back toward math."""
    cues = {"math", "problem", "count", "add", "number", "let's", "let us", "try", "want to"}
    lower = reply.lower()
    found = any(cue in lower for cue in cues)
    return {
        "key": "redirect_to_math",
        "score": int(found),
        "reason": f"math redirect cue {'found' if found else 'missing'} in reply",
    }


# ── LLM-as-judge evaluator ────────────────────────────────────────────────────

def no_spoiler(problem: str, reply: str, answer: str) -> dict:
    """
    Ask Claude Haiku whether Lumi revealed the correct answer before the child
    had a chance to try.  Score 1 = no spoiler, 0 = answer was leaked.
    """
    prompt = (
        f'A child asked their math tutor: "{problem}"\n'
        f'The tutor replied: "{reply}"\n'
        f'The correct answer is {answer}.\n\n'
        f"Did the tutor's reply reveal the answer ({answer}) to the child "
        f"before the child had a chance to try? "
        f"Answer YES or NO on the first line, then one sentence explaining why."
    )
    r = _judge.messages.create(
        model=_JUDGE_MODEL,
        max_tokens=120,
        messages=[{"role": "user", "content": prompt}],
    )
    text = r.content[0].text.strip()
    spoiled = text.upper().startswith("YES")
    return {
        "key": "no_spoiler",
        "score": 0 if spoiled else 1,
        "reason": text,
    }


# ── LangSmith-compatible wrappers ─────────────────────────────────────────────
# These accept (outputs, reference_outputs) as required by langsmith.evaluate().
# EvaluationResult uses "comment" not "reason", so we remap before returning.

def _to_ls(result: dict) -> dict:
    """Rename 'reason' → 'comment' so LangSmith's EvaluationResult accepts it."""
    out = {k: v for k, v in result.items() if k != "reason"}
    if "reason" in result:
        out["comment"] = result["reason"]
    return out


def ls_tool_compliance(outputs: dict, reference_outputs: dict) -> dict:
    return _to_ls(tools_called(outputs["tool_log"], set(reference_outputs["required_tools"])))


def ls_response_length(outputs: dict, reference_outputs: dict) -> dict:
    return _to_ls(response_length(outputs["reply"]))


def ls_no_spoiler(outputs: dict, reference_outputs: dict) -> dict:
    return _to_ls(no_spoiler(
        reference_outputs["user_input"],
        outputs["reply"],
        reference_outputs["answer"],
    ))


def ls_redirects_to_math(outputs: dict, reference_outputs: dict) -> dict:
    return _to_ls(redirects_to_math(outputs["reply"]))
