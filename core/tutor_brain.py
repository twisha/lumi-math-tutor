import json
import os
import re

import anthropic

from core.prompts import SYSTEM_PROMPT
from core.mcp_bridge import TOOLS_ANTHROPIC, execute_tool

MODEL = os.getenv("LUMI_MODEL", "claude-haiku-4-5-20251001")

if not os.getenv("ANTHROPIC_API_KEY"):
    raise EnvironmentError(
        "ANTHROPIC_API_KEY is not set. "
        "Copy .env.example to .env and add your key, then run: export $(cat .env | xargs)"
    )

client = anthropic.Anthropic()

conversation_history: list[dict] = []


def _clean(text: str) -> str:
    text = re.sub(r'\\\((.+?)\\\)', r'\1', text)
    text = re.sub(r'\\\[(.+?)\\\]', r'\1', text)
    return text.strip()


def ask_lumi(user_text: str) -> tuple[str, list[dict]]:
    conversation_history.append({"role": "user", "content": user_text})
    tool_calls_log = []

    while True:
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=300,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
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

                    try:
                        result = execute_tool(block.name, dict(block.input))
                    except Exception as e:
                        result = json.dumps({"error": str(e)})

                    tool_calls_log.append({
                        "tool": block.name,
                        "args": dict(block.input),
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
            # content must always be a list for Anthropic API consistency
            conversation_history.append({
                "role": "assistant",
                "content": [{"type": "text", "text": reply}]
            })
            return reply, tool_calls_log


def reset_conversation():
    conversation_history.clear()


def get_history():
    return conversation_history.copy()
