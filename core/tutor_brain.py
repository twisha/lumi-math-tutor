import json
import os
import re
from openai import OpenAI
from core.prompts import SYSTEM_PROMPT
from core.mcp_bridge import TOOLS, execute_tool

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
MODEL = os.getenv("LUMI_MODEL", "mistral")

client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
conversation_history = []


def _clean(text: str) -> str:
    text = re.sub(r'\\\((.+?)\\\)', r'\1', text)
    text = re.sub(r'\\\[(.+?)\\\]', r'\1', text)
    return text.strip()


def ask_lumi(user_text: str) -> tuple[str, list[dict]]:
    conversation_history.append({"role": "user", "content": user_text})
    tool_calls_log = []

    while True:
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=200,
            tools=TOOLS,
            tool_choice="auto",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *conversation_history
            ]
        )

        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        if message.tool_calls:
            conversation_history.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            })

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                result = execute_tool(tool_name, tool_args)

                tool_calls_log.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "result": json.loads(result)
                })

                conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

        else:
            reply = _clean(message.content or "")
            conversation_history.append({"role": "assistant", "content": reply})
            return reply, tool_calls_log


def reset_conversation():
    conversation_history.clear()


def get_history():
    return conversation_history.copy()
