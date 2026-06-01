"""
Lumi Math Tutor — Chainlit UI
Run with: chainlit run chainlit_app.py
"""
import asyncio
import threading

import chainlit as cl

from core.tutor_brain import ask_lumi, reset_conversation
from core.speech_input import record_audio, transcribe
from core.speech_output import speak


def _speak_async(text: str):
    threading.Thread(target=speak, args=(text,), daemon=True).start()


@cl.on_chat_start
async def on_chat_start():
    reset_conversation()
    intro = "Hi! I am Lumi, your math buddy! What math shall we do today? 😊"
    await cl.Message(content=intro, author="Lumi ✨").send()
    _speak_async(intro)


@cl.on_message
async def on_message(message: cl.Message):
    user_text = message.content.strip()
    if not user_text:
        return

    loop = asyncio.get_event_loop()

    async with cl.Step(name="Lumi is thinking", type="run") as thinking_step:
        thinking_step.input = user_text

        reply, tool_calls = await loop.run_in_executor(None, ask_lumi, user_text)

        for tc in tool_calls:
            async with cl.Step(name=tc["tool"], type="tool") as tool_step:
                tool_step.input = tc["args"]
                tool_step.output = tc["result"]

        thinking_step.output = reply

    await cl.Message(content=reply, author="Lumi ✨").send()
    _speak_async(reply)


@cl.on_audio_end
async def on_audio_end(elements):
    if not elements:
        return

    audio_data = b"".join(e.content for e in elements if hasattr(e, "content"))
    if not audio_data:
        return

    import numpy as np
    audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

    await cl.Message(content="🎤 Transcribing...").send()

    loop = asyncio.get_event_loop()
    child_text = await loop.run_in_executor(None, transcribe, audio_array)

    if not child_text:
        await cl.Message(content="I didn't catch that — could you try again? 😊").send()
        return

    await cl.Message(content=child_text, author="You").send()

    async with cl.Step(name="Lumi is thinking", type="run") as thinking_step:
        thinking_step.input = child_text
        reply, tool_calls = await loop.run_in_executor(None, ask_lumi, child_text)

        for tc in tool_calls:
            async with cl.Step(name=tc["tool"], type="tool") as tool_step:
                tool_step.input = tc["args"]
                tool_step.output = tc["result"]

        thinking_step.output = reply

    await cl.Message(content=reply, author="Lumi ✨").send()
    _speak_async(reply)
