import json
import os
import re

import anthropic
from langsmith import traceable
from langsmith.wrappers import wrap_anthropic

from core.prompts import get_system_prompt
from core.mcp_bridge import TOOLS_ANTHROPIC, execute_tool
from core.storage import record_misconception

MODEL = os.getenv("LUMI_MODEL", "claude-haiku-4-5-20251001")

if not os.getenv("ANTHROPIC_API_KEY"):
    raise EnvironmentError(
        "ANTHROPIC_API_KEY is not set. "
        "Copy .env.example to .env and add your key, then run: export $(cat .env | xargs)"
    )

# wrap_anthropic traces every client.messages.create() call in LangSmith
client = wrap_anthropic(anthropic.Anthropic())

conversation_history: list[dict] = []

# Tools that need grade_group injected before execution
_GRADE_AWARE_TOOLS = {"generate_problem", "check_grade_level", "classify_misconception"}

# Cap on model↔tool round-trips per turn. A well-behaved turn uses 1–2
# (e.g. calculate → check_answer → text). The ceiling stops a runaway loop
# where the model keeps requesting tools indefinitely (unbounded cost/latency).
_MAX_TOOL_ITERATIONS = 6


def _looks_like_answer(text: str) -> bool:
    """Return True when the child typed a bare number (likely answering a problem)."""
    return bool(re.match(r'^\s*\d+\s*$', text.strip()))


def _clean(text: str) -> tuple[str, int]:
    """Strip LaTeX escapes and extract the [COUNT:N] tag if present.
    Returns (cleaned_text, count_n) where count_n=0 means no counting task."""
    text = re.sub(r'\\\((.+?)\\\)', r'\1', text)
    text = re.sub(r'\\\[(.+?)\\\]', r'\1', text)
    m = re.search(r'\[COUNT:(\d+)\]', text, re.IGNORECASE)
    count_n = int(m.group(1)) if m else 0
    text = re.sub(r'\s*\[COUNT:\d+\]\s*$', '', text, flags=re.IGNORECASE).strip()
    return text, count_n


def _persist_misconceptions(tool_calls_log: list[dict], student_id: str, grade_group: str) -> None:
    """Save any classified misconceptions from this turn to the DB."""
    for tc in tool_calls_log:
        if tc.get("tool") == "classify_misconception":
            misconception = tc.get("result", {}).get("misconception", "unknown_error")
            if misconception != "unknown_error":
                record_misconception(student_id, misconception, grade_group)


@traceable(name="ask_lumi", run_type="chain")
def ask_lumi(
    user_text: str,
    grade_group: str = "K2",
    student_id: str = "",
    history: list[dict] | None = None,
) -> tuple[str, list[dict], int]:
    # Each browser session must own its own history. app.py passes a per-session
    # list; the module-level global is only a fallback for single-threaded callers
    # (evals, tests). Sharing one global across concurrent users leaks turns
    # between children.
    history = conversation_history if history is None else history
    history.append({"role": "user", "content": user_text})
    tool_calls_log = []
    system_prompt = get_system_prompt(grade_group)

    tool_choice = {"type": "any"} if _looks_like_answer(user_text) else {"type": "auto"}

    for _iteration in range(_MAX_TOOL_ITERATIONS):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=300,
                system=[{
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"}
                }],
                tools=TOOLS_ANTHROPIC,
                tool_choice=tool_choice,
                messages=history
            )
        except anthropic.AuthenticationError:
            history.pop()
            return "Oops! There is a problem with my connection. Please check the API key.", [], 0
        except anthropic.RateLimitError:
            history.pop()
            return "I am a little tired right now! Please try again in a moment. 😊", [], 0
        except anthropic.APIError as e:
            history.pop()
            return f"Something went wrong — please try again! ({type(e).__name__})", [], 0

        if response.stop_reason == "tool_use":
            assistant_content = []
            tool_results = []

            for block in response.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })

                    # Inject grade_group for tools that need it
                    args = dict(block.input)
                    if block.name in _GRADE_AWARE_TOOLS:
                        args["grade_group"] = grade_group

                    try:
                        result = execute_tool(block.name, args)
                    except Exception as e:
                        result = json.dumps({"error": str(e)})

                    tool_calls_log.append({
                        "tool": block.name,
                        "args": args,
                        "result": json.loads(result)
                    })

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            history.append({"role": "assistant", "content": assistant_content})
            history.append({"role": "user", "content": tool_results})
            tool_choice = {"type": "auto"}  # allow text-only response after tool results

        else:
            raw = "".join(block.text for block in response.content if hasattr(block, "text"))
            reply, is_counting = _clean(raw)
            history.append({
                "role": "assistant",
                "content": [{"type": "text", "text": reply}]
            })
            if student_id:
                _persist_misconceptions(tool_calls_log, student_id, grade_group)
            return reply, tool_calls_log, is_counting

    # Budget exhausted while the model was still requesting tools — bail out with
    # a safe, in-character reply rather than looping forever. History already ends
    # with a tool_result, so the next turn can continue normally.
    if student_id:
        _persist_misconceptions(tool_calls_log, student_id, grade_group)
    fallback = "Let's try that one together! What do you think the answer is? 😊"
    history.append({"role": "assistant", "content": [{"type": "text", "text": fallback}]})
    return fallback, tool_calls_log, 0


def reset_conversation(history: list[dict] | None = None):
    (conversation_history if history is None else history).clear()


def get_history():
    return conversation_history.copy()
