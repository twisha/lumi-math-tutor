# ✨ Lumi — Math Buddy

A locally-run, voice-enabled AI math tutor for Kindergarten through 2nd grade (ages 5–7). Lumi guides children through counting, addition, and subtraction using a warm, patient, and playful persona — with no data ever sent to the cloud.

## Features

- **Voice input** — child speaks; Whisper transcribes locally
- **Voice output** — Lumi responds aloud via pyttsx3
- **Agentic tool use** — Lumi calls tools to verify answers before responding (no hallucinated math)
- **Guardrails** — redirects off-topic chat and out-of-grade questions warmly
- **Debug panel** — toggle to inspect tool calls in the sidebar
- **100% local** — Ollama + Whisper + pyttsx3, no API keys required

## What Lumi Teaches

- Counting (1–20)
- Number recognition and ordering
- Addition and subtraction within 20
- Simple word problems using everyday objects

## Tech Stack

| Component | Technology |
|---|---|
| UI | Streamlit |
| LLM | llama3.2 via Ollama |
| LLM API | OpenAI-compatible client → `localhost:11434` |
| Speech input | OpenAI Whisper (local) |
| Speech output | pyttsx3 |
| Audio recording | sounddevice + scipy |

## Prerequisites

- Python 3.9+
- [Ollama](https://ollama.com) installed and running

## Setup

1. **Clone the repo**
   ```bash
   git clone <repo-url>
   cd CapstoneProject
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Pull the model**
   ```bash
   ollama pull llama3.2
   ```

## Running the App

In one terminal, start Ollama:
```bash
ollama serve
```

In another terminal, start the app:
```bash
streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser and click **Start Session with Lumi!**

## Project Structure

```
CapstoneProject/
├── app.py              # Streamlit UI
├── requirements.txt    # Python dependencies
├── core/
│   ├── prompts.py      # Lumi's system prompt and persona
│   ├── tutor_brain.py  # Agentic loop (tool calls + conversation history)
│   ├── tools.py        # Tool definitions and execute_tool()
│   ├── speech_input.py # Mic recording + Whisper transcription
│   └── speech_output.py# pyttsx3 text-to-speech
```

## Usage

| Input method | How |
|---|---|
| Voice | Click **Tap to Talk!**, speak for up to 5 seconds |
| Text | Type in the text box and click **Send** |
| New session | Click **New Session** in the sidebar |
| Debug tools | Toggle **Show tool calls** in the sidebar |
