import json
import os
import re

import anthropic
from langsmith import traceable
from langsmith.wrappers import wrap_anthropic

from core.prompts import get_system_prompt
from core.mcp_bridge import TOOLS_ANTHROPIC, execute_tool

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
_GRADE_AWARE_TOOLS = {"generate_problem", "check_grade_level"}


def _clean(text: str) -> str:
    text = re.sub(r'\\\((.+?)\\\)', r'\1', text)
    text = re.sub(r'\\\[(.+?)\\\]', r'\1', text)
    return text.strip()


@traceable(name="ask_lumi", run_type="chain")
def ask_lumi(user_text: str, grade_group: str = "K2") -> tuple[str, list[dict]]:
    conversation_history.append({"role": "user", "content": user_text})
    tool_calls_log = []
    system_prompt = get_system_prompt(grade_group)

    while True:
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
                messages=conversation_history
            )
        except anthropic.AuthenticationError:
            conversation_history.pop()
            return "Oops! There is a problem with my connection. Please check the API key.", []
        except anthropic.RateLimitError:
            conversation_history.pop()
            return "I am a little tired right now! Please try again in a moment. 😊", []
        except anthropic.APIError as e:
            conversation_history.pop()
            return f"Something went wrong — please try again! ({type(e).__name__})", []

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

            conversation_history.append({"role": "assistant", "content": assistant_content})
            conversation_history.append({"role": "user", "content": tool_results})

        else:
            reply = _clean("".join(
                block.text for block in response.content
                if hasattr(block, "text")
            ))
            conversation_history.append({
                "role": "assistant",
                "content": [{"type": "text", "text": reply}]
            })
            return reply, tool_calls_log


def reset_conversation():
    conversation_history.clear()


def get_history():
    return conversation_history.copy()
