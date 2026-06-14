"""
Lumi Math Tutor — app.py
Streamlit UI for a K-2 voice math tutor powered by Claude API + MCP tools + local Whisper + pyttsx3.

Run with:
    export $(cat .env | xargs) && streamlit run app.py
"""

import time
import threading
import streamlit as st
from core.tutor_brain import ask_lumi, reset_conversation
from core.speech_input import record_audio, transcribe, list_input_devices
from core.speech_output import speak, stop_speaking
from core.visual_aids import detect_k2_problem, render_k2_visual

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Lumi Math Tutor",
    page_icon="⭐",
    layout="centered"
)

# ── Styling ───────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Fredoka+One&family=Nunito:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Nunito', sans-serif;
        background-color: #FFF9F0;
    }

    /* Header */
    .lumi-header {
        text-align: center;
        padding: 1.5rem 0 0.5rem;
    }
    .lumi-title {
        font-family: 'Fredoka One', cursive;
        font-size: 3.2rem;
        color: #FF8C00;
        margin: 0;
        line-height: 1.1;
    }
    .lumi-subtitle {
        font-size: 1.1rem;
        color: #888;
        margin-top: 0.2rem;
    }

    /* Chat bubbles */
    .bubble-lumi {
        background: #FFF3CD;
        border: 2px solid #FFD966;
        border-radius: 20px 20px 20px 4px;
        padding: 14px 18px;
        margin: 8px 0;
        font-size: 1.15rem;
        color: #333;
        max-width: 85%;
    }
    .bubble-child {
        background: #D4EDFF;
        border: 2px solid #90CAF9;
        border-radius: 20px 20px 4px 20px;
        padding: 14px 18px;
        margin: 8px 0 8px auto;
        font-size: 1.15rem;
        color: #1a1a1a;
        max-width: 75%;
        text-align: right;
    }
    .bubble-system {
        background: #F0F0F0;
        border-radius: 12px;
        padding: 8px 14px;
        margin: 4px auto;
        font-size: 0.82rem;
        color: #999;
        text-align: center;
        max-width: 60%;
    }

    /* Tool debug panel */
    .tool-badge {
        display: inline-block;
        background: #EDE7F6;
        color: #5E35B1;
        border-radius: 8px;
        padding: 2px 8px;
        font-size: 0.75rem;
        font-family: monospace;
        margin: 2px;
    }

    /* Buttons */
    .stButton > button {
        font-family: 'Fredoka One', cursive;
        font-size: 1.2rem;
        border-radius: 50px;
        padding: 0.6rem 2rem;
        border: none;
        transition: transform 0.1s ease;
    }
    .stButton > button:hover {
        transform: scale(1.03);
    }
    /* Tap to Talk — high contrast: dark text on vivid amber */
    .stButton > button[kind="primary"] {
        background-color: #FFB300 !important;
        color: #1a1a1a !important;
        font-size: 1.3rem !important;
        font-weight: 700 !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #FFA000 !important;
        color: #1a1a1a !important;
    }

    /* Status bar */
    .status-bar {
        text-align: center;
        font-size: 0.9rem;
        color: #aaa;
        padding: 0.3rem;
    }

    /* Divider */
    hr { border-color: #FFD966; opacity: 0.4; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "status" not in st.session_state:
    st.session_state.status = "Ready!"
if "show_tools" not in st.session_state:
    st.session_state.show_tools = False
if "session_started" not in st.session_state:
    st.session_state.session_started = False
if "grade_group" not in st.session_state:
    st.session_state.grade_group = None     # "K2" or "35"
if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = True   # always on for K-2; optional for 3-5
if "last_recording_end" not in st.session_state:
    st.session_state.last_recording_end = 0.0
if "active_k2_problem" not in st.session_state:
    st.session_state.active_k2_problem = None  # (a, b, op) of current problem
if "mic_device" not in st.session_state:
    st.session_state.mic_device = None  # None = auto-select

# recording is set and cleared within a single script run — reset each run so
# a crash or queued double-click can never leave the button permanently disabled.
st.session_state.recording = False

# ── Helper functions ──────────────────────────────────────────────────────────

import re as _re

def _extract_problem_from_tools(tools: list):
    """Parse (a, b, op) from a calculate() tool call expression, e.g. '8+5' → (8,5,'+')."""
    for tc in tools:
        if tc.get("tool") == "calculate":
            expr = tc.get("result", {}).get("expression", "")
            m = _re.match(r'(\d+)\s*([+\-])\s*(\d+)', expr)
            if m:
                a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
                if 0 <= a <= 20 and 0 <= b <= 20:
                    return (a, b, op)
    return None

_HELP_PHRASES = ("help", "teach", "don't know", "not sure", "confused",
                 "explain", "show me", "how do", "stuck", "i don't", "no idea")

def _should_show_visual(child_text: str, tools: list) -> bool:
    """Return True when the child asks for help or gives a wrong answer."""
    if any(p in child_text.lower() for p in _HELP_PHRASES):
        return True
    for tc in tools:
        if tc.get("tool") == "check_answer":
            if not tc.get("result", {}).get("correct", True):
                return True
    return False

def add_message(role: str, text: str, tools: list = None,
                show_visual: bool = False, count_n: int = 0):
    tools = tools or []
    problem = None
    if role == "lumi" and st.session_state.grade_group == "K2":
        detected = _extract_problem_from_tools(tools) or detect_k2_problem(text)
        if detected:
            st.session_state.active_k2_problem = detected
        if show_visual and st.session_state.active_k2_problem:
            problem = st.session_state.active_k2_problem
    st.session_state.messages.append({
        "role": role,
        "text": text,
        "tools": tools,
        "problem": problem,
        "count_n": count_n,
    })

def speak_async(text: str):
    """Speak without blocking the UI."""
    thread = threading.Thread(target=speak, args=(text,), daemon=True)
    thread.start()

def start_session(grade_group: str):
    """Initialize a fresh tutoring session for the selected grade group."""
    reset_conversation()
    st.session_state.messages = []
    st.session_state.session_started = True
    st.session_state.grade_group = grade_group
    st.session_state.active_k2_problem = None
    # Voice defaults on for K-2, off for 3-5 (can be toggled in sidebar)
    st.session_state.voice_enabled = (grade_group == "K2")
    if grade_group == "35":
        intro = "Hey there! I am Lumi, your math tutor! Ready to tackle multiplication, division, or fractions today?"
    else:
        intro = "Hi! I am Lumi, your math buddy! What math shall we do today?"
    add_message("lumi", intro)
    if st.session_state.voice_enabled:
        speak_async(intro)

_RECORDING_COOLDOWN = 2.0  # seconds to ignore a queued double-click after recording ends

def _recording_duration() -> int:
    """Compute recording window from Lumi's [COUNT:N] tag: N sec + 3 s buffer, min 4, max 30."""
    for msg in reversed(st.session_state.get("messages", [])):
        if msg["role"] == "lumi":
            n = msg.get("count_n", 0)
            return min(30, max(4, n + 3)) if n else 4
    return 4

def handle_voice_input():
    """Record, transcribe, and send to Lumi."""
    # Discard any click that was queued while the previous recording was still running.
    if time.time() - st.session_state.last_recording_end < _RECORDING_COOLDOWN:
        return

    stop_speaking()  # silence Lumi so mic doesn't pick up speaker output
    st.session_state.recording = True
    msg = st.empty()

    try:
        rec_secs = _recording_duration()
        msg.info(f"🎤 Listening... speak now! ({rec_secs} seconds)")
        audio = record_audio(duration=rec_secs, device=st.session_state.mic_device)

        # Mic health check — warn if device returns pure silence
        import numpy as _np
        rms = float(_np.sqrt(_np.mean(audio ** 2)))
        if rms < 1e-6:
            st.session_state.status = "⚠️ Mic returned silence — check mic permissions in System Settings → Privacy & Security → Microphone"
            return

        msg.info("💭 Transcribing your voice...")
        child_text = transcribe(audio)

        if not child_text:
            st.session_state.status = "🎤 Didn't catch that — please try again!"
            return

        msg.success(f'You said: *"{child_text}"*')
        add_message("child", child_text)

        msg.info("😊 Lumi is thinking...")
        reply, tools, count_n = ask_lumi(child_text, st.session_state.grade_group or "K2")
        show_vis = _should_show_visual(child_text, tools) if st.session_state.grade_group == "K2" else False
        add_message("lumi", reply, tools, show_visual=show_vis, count_n=count_n)
        if st.session_state.voice_enabled:
            speak_async(reply)
        msg.empty()
        st.session_state.status = "Ready!"

    except Exception as e:
        st.session_state.status = f"⚠️ Error: {type(e).__name__} — {e}"

    finally:
        st.session_state.recording = False
        st.session_state.last_recording_end = time.time()

def handle_text_input(text: str):
    """Send typed text to Lumi."""
    if not text.strip():
        return
    add_message("child", text)
    st.session_state.status = "Lumi is thinking..."
    reply, tools, count_n = ask_lumi(text, st.session_state.grade_group or "K2")
    show_vis = _should_show_visual(text, tools) if st.session_state.grade_group == "K2" else False
    add_message("lumi", reply, tools, show_visual=show_vis, count_n=count_n)
    if st.session_state.voice_enabled:
        speak_async(reply)
    st.session_state.status = "Ready!"

# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="lumi-header">
    <div class="lumi-title">✨ Lumi ✨</div>
    <div class="lumi-subtitle">Your Math Buddy</div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### ⚙️ Settings")
    st.session_state.show_tools = st.toggle(
        "Show tool calls (debug)",
        value=st.session_state.show_tools
    )

    # Mic device selector
    _input_devs = list_input_devices()
    _dev_labels = ["🔄 Auto"] + [f"🎤 {d['name']}" for d in _input_devs]
    _dev_indices = [None] + [d["index"] for d in _input_devs]
    _current = _dev_indices.index(st.session_state.mic_device) if st.session_state.mic_device in _dev_indices else 0
    _selected = st.selectbox("🎙️ Microphone", _dev_labels, index=_current)
    st.session_state.mic_device = _dev_indices[_dev_labels.index(_selected)]

    if st.session_state.grade_group == "35":
        st.session_state.voice_enabled = st.toggle(
            "🎤 Voice I/O",
            value=st.session_state.voice_enabled,
            help="Grade 3-5 students can type — toggle voice on or off anytime."
        )
    else:
        st.session_state.voice_enabled = True  # always on for K-2

    st.markdown("---")
    if st.session_state.grade_group == "K2":
        st.markdown("### 📚 K–2 Topics")
        st.markdown("""
    - Counting (1–20)
    - Addition within 20
    - Subtraction within 20
    - Number recognition
    - Simple word problems
    """)
    elif st.session_state.grade_group == "35":
        st.markdown("### 📚 Grade 3–5 Topics")
        st.markdown("""
    - Multiplication (1–12)
    - Division within 144
    - Add/Subtract within 1,000
    - Basic fractions
    - Multi-step word problems
    """)
    else:
        st.markdown("### 📚 Select a grade to begin")

    st.markdown("---")
    st.markdown("### 🛡️ Guardrails Active")
    st.markdown("""
    - ✅ Off-topic redirect
    - ✅ Grade level check
    - ✅ Verified arithmetic
    """)

    st.markdown("---")
    if st.session_state.session_started:
        if st.button("🔄 New Session", use_container_width=True):
            st.session_state.session_started = False
            st.session_state.grade_group = None
            reset_conversation()
            st.session_state.messages = []
            st.rerun()

# ── Grade picker (shown before session starts) ────────────────────────────────

if not st.session_state.session_started:
    st.markdown("""
    <div style='text-align:center; padding: 1rem 0 1.5rem;'>
        <p style='color:#aaa; font-size:1.1rem;'>Who are we tutoring today?</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div style='background:#FFF3CD; border:2px solid #FFD966; border-radius:16px;
                    padding:1.5rem; text-align:center; min-height:160px;'>
            <div style='font-size:2rem;'>🌱</div>
            <div style='font-size:1.3rem; font-weight:700; color:#FF8C00;'>K – 2</div>
            <div style='color:#666; font-size:0.9rem; margin-top:0.4rem;'>Ages 5–7</div>
            <div style='color:#888; font-size:0.82rem; margin-top:0.6rem;'>
                Counting · Addition · Subtraction
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("▶️ Start K–2 Session", use_container_width=True, type="primary"):
            start_session("K2")
            st.rerun()

    with col2:
        st.markdown("""
        <div style='background:#E8F4FF; border:2px solid #90CAF9; border-radius:16px;
                    padding:1.5rem; text-align:center; min-height:160px;'>
            <div style='font-size:2rem;'>🚀</div>
            <div style='font-size:1.3rem; font-weight:700; color:#1565C0;'>Grade 3 – 5</div>
            <div style='color:#666; font-size:0.9rem; margin-top:0.4rem;'>Ages 8–10</div>
            <div style='color:#888; font-size:0.82rem; margin-top:0.6rem;'>
                Multiply · Divide · Fractions
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("▶️ Start Grade 3–5 Session", use_container_width=True):
            start_session("35")
            st.rerun()

    st.stop()

# ── Chat history ──────────────────────────────────────────────────────────────

chat_container = st.container()

with chat_container:
    for msg in st.session_state.messages:
        if msg["role"] == "lumi":
            st.markdown(
                f'<div class="bubble-lumi">😊 <b>Lumi:</b> {msg["text"]}</div>',
                unsafe_allow_html=True
            )
            # K-2 visual aid: only shown when child is struggling or asks for help
            if msg.get("problem"):
                st.markdown(render_k2_visual(*msg["problem"]), unsafe_allow_html=True)
            # Show tool calls if debug mode is on
            if st.session_state.show_tools and msg["tools"]:
                with st.expander("🔧 Tools used", expanded=False):
                    for tc in msg["tools"]:
                        st.markdown(
                            f'<span class="tool-badge">{tc["tool"]}</span>',
                            unsafe_allow_html=True
                        )
                        col1, col2 = st.columns(2)
                        with col1:
                            st.caption("Args")
                            st.json(tc["args"])
                        with col2:
                            st.caption("Result")
                            st.json(tc["result"])

        elif msg["role"] == "child":
            st.markdown(
                f'<div class="bubble-child">{msg["text"]} 👦</div>',
                unsafe_allow_html=True
            )

        elif msg["role"] == "system":
            st.markdown(
                f'<div class="bubble-system">{msg["text"]}</div>',
                unsafe_allow_html=True
            )

# ── Status ────────────────────────────────────────────────────────────────────

st.markdown(
    f'<div class="status-bar">{st.session_state.status}</div>',
    unsafe_allow_html=True
)

st.markdown("---")

# ── Input area ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
.voice-hint { text-align:center; color:#aaa; font-size:0.8rem; margin-top:-0.4rem; }
</style>
""", unsafe_allow_html=True)

if st.session_state.voice_enabled:
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.session_state.recording:
            st.button("⏺️ Recording...", use_container_width=True, disabled=True)
        else:
            if st.button("🎤  Tap to Talk!", use_container_width=True, type="primary"):
                handle_voice_input()
                st.rerun()
        st.markdown(f'<div class="voice-hint">{_recording_duration()} sec · auto-stops</div>', unsafe_allow_html=True)
    text_col_container = col2
else:
    text_col_container = st.container()

with text_col_container:
    with st.form("text_form", clear_on_submit=True):
        text_col, btn_col = st.columns([4, 1])
        with text_col:
            typed = st.text_input(
                "Or type here",
                placeholder="Type your answer...",
                label_visibility="collapsed"
            )
        with btn_col:
            submitted = st.form_submit_button("Send")

        if submitted and typed:
            handle_text_input(typed)
            st.rerun()

# ── Footer ────────────────────────────────────────────────────────────────────

st.markdown("""
<div style='text-align:center; color:#ccc; font-size:0.75rem; padding-top:1rem'>
    Powered by Claude API + Whisper + pyttsx3 · Tools via MCP · Speech runs locally
</div>
""", unsafe_allow_html=True)
