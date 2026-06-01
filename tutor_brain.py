import json
from openai import OpenAI
from core.prompts import SYSTEM_PROMPT
from core.tools import TOOLS, execute_tool

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

MODEL = "llama3.2"
conversation_history = []


def ask_lumi(user_text: str) -> tuple[str, list[dict]]:
    """
    Send child's message to Ollama with tools.
    Returns (reply, tool_calls_log) so the UI can show what happened.
    """
    conversation_history.append({
        "role": "user",
        "content": user_text
    })

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

        # ── Model wants to call a tool ──
        if finish_reason == "tool_calls" and message.tool_calls:
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

                # Log for UI display
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

        # ── Model has final response ──
        else:
            reply = (message.content or "").strip()
            conversation_history.append({
                "role": "assistant",
                "content": reply
            })
            return reply, tool_calls_log


def reset_conversation():
    """Clear history for a fresh session."""
    conversation_history.clear()


def get_history():
    """Return conversation history for display."""
    return conversation_history.copy()
