"""
Lumi Math Tutor — app.py
Streamlit UI for a K-2 voice math tutor powered by Ollama + local Whisper + pyttsx3.

Run with:
    streamlit run app.py
Make sure Ollama is running in another terminal:
    ollama serve
"""

import threading
import streamlit as st
from core.tutor_brain import ask_lumi, reset_conversation
from core.speech_input import record_audio, transcribe
from core.speech_output import speak

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
    st.session_state.messages = []          # list of {role, text, tools}
if "recording" not in st.session_state:
    st.session_state.recording = False
if "status" not in st.session_state:
    st.session_state.status = "Ready!"
if "show_tools" not in st.session_state:
    st.session_state.show_tools = False
if "session_started" not in st.session_state:
    st.session_state.session_started = False

# ── Helper functions ──────────────────────────────────────────────────────────

def add_message(role: str, text: str, tools: list = None):
    st.session_state.messages.append({
        "role": role,
        "text": text,
        "tools": tools or []
    })

def speak_async(text: str):
    """Speak without blocking the UI."""
    thread = threading.Thread(target=speak, args=(text,), daemon=True)
    thread.start()

def start_session():
    """Initialize a fresh tutoring session."""
    reset_conversation()
    st.session_state.messages = []
    st.session_state.session_started = True
    intro = "Hi! I am Lumi, your math buddy! What math shall we do today?"
    add_message("lumi", intro)
    speak_async(intro)

def handle_voice_input():
    """Record, transcribe, and send to Lumi."""
    st.session_state.status = "Listening... speak now!"
    st.session_state.recording = True

    try:
        # Record
        audio_file = record_audio(duration=5)
        st.session_state.status = "Thinking..."

        # Transcribe
        child_text = transcribe(audio_file)
        if not child_text:
            st.session_state.status = "I didn't hear anything — try again!"
            st.session_state.recording = False
            return

        add_message("child", child_text)
        st.session_state.status = "Lumi is thinking..."

        # Get Lumi's response
        reply, tools = ask_lumi(child_text)
        add_message("lumi", reply, tools)
        speak_async(reply)
        st.session_state.status = "Ready!"

    except Exception as e:
        st.session_state.status = f"Error: {str(e)}"

    st.session_state.recording = False

def handle_text_input(text: str):
    """Send typed text to Lumi (fallback for testing)."""
    if not text.strip():
        return
    add_message("child", text)
    st.session_state.status = "Lumi is thinking..."
    reply, tools = ask_lumi(text)
    add_message("lumi", reply, tools)
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

    st.markdown("---")
    st.markdown("### 📚 What Lumi Teaches")
    st.markdown("""
    - Counting (1–20)
    - Addition within 20
    - Subtraction within 20
    - Number recognition
    - Simple word problems
    """)

    st.markdown("---")
    st.markdown("### 🛡️ Guardrails Active")
    st.markdown("""
    - ✅ Off-topic redirect
    - ✅ Grade level check
    - ✅ Verified arithmetic
    """)

    st.markdown("---")
    if st.button("🔄 New Session", use_container_width=True):
        start_session()
        st.rerun()

# ── Start session if not started ──────────────────────────────────────────────

if not st.session_state.session_started:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("▶️ Start Session with Lumi!", use_container_width=True):
            start_session()
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

col1, col2 = st.columns([1, 2])

with col1:
    voice_label = "⏺️ Recording..." if st.session_state.recording else "🎤 Tap to Talk!"
    voice_disabled = st.session_state.recording

    if st.button(voice_label, use_container_width=True, disabled=voice_disabled):
        handle_voice_input()
        st.rerun()

with col2:
    # Text input as fallback
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
    Powered by Ollama + Whisper + pyttsx3 · Runs 100% locally · No data sent to the cloud
</div>
""", unsafe_allow_html=True)
