# ✨ Lumi — Math Buddy

A voice-enabled AI math tutor for Kindergarten through 2nd grade (ages 5–7). Lumi guides children through counting, addition, and subtraction using a warm, patient, and playful persona — powered by Claude AI with MCP-based tool use.

## Features

- **Voice input** — child speaks; Whisper transcribes locally
- **Voice output** — Lumi responds aloud via pyttsx3
- **Agentic tool use** — Lumi calls tools via MCP to verify answers (no hallucinated math)
- **Guardrails** — redirects off-topic chat and out-of-grade questions warmly
- **Prompt caching** — system prompt is cached with the Anthropic API to reduce latency and cost
- **Debug panel** — toggle to inspect tool calls in the sidebar

## What Lumi Teaches

- Counting (1–20)
- Number recognition and ordering
- Addition and subtraction within 20
- Simple word problems using everyday objects

## Tech Stack

| Component | Technology |
| --- | --- |
| UI | Streamlit |
| LLM | Claude Haiku via Anthropic API (configurable via `LUMI_MODEL`) |
| Tool protocol | MCP (Model Context Protocol) |
| Speech input | OpenAI Whisper (local) |
| Speech output | pyttsx3 |
| Audio recording | sounddevice |

## Architecture

```mermaid
flowchart TD
    subgraph IO["I/O Layer"]
        MIC["🎤 Mic\nsounddevice"] --> WHISPER["Whisper\nspeech_input.py"]
        TTS["🔊 pyttsx3\nspeech_output.py"]
    end

    subgraph UI["UI Layer"]
        APP["Streamlit\napp.py"]
    end

    subgraph Brain["Brain Layer"]
        BRAIN["tutor_brain.py\nAgentic Loop"]
        CLAUDE["Claude API\nAnthropic"]
    end

    subgraph MCP["MCP Layer"]
        BRIDGE["mcp_bridge.py\nMCP Client"]
        SERVER["mcp_server.py\nMCP Server"]
    end

    subgraph Tools["Tools Layer"]
        TOOLS["tools.py\ncalculate · check_answer\ngenerate_problem · check_topic\ncheck_grade_level"]
    end

    CHILD["👦 Child"] -->|voice| MIC
    CHILD -->|text| APP
    WHISPER -->|transcript| APP
    APP -->|message| BRAIN
    BRAIN <-->|"chat + tools (cached)"| CLAUDE
    BRAIN -->|execute_tool| BRIDGE
    BRIDGE <-->|"stdio (MCP protocol)"| SERVER
    SERVER --> TOOLS
    BRAIN -->|reply| APP
    APP -->|speak| TTS
```

## Prerequisites

- Python 3.9+
- [Anthropic API key](https://console.anthropic.com)

## Setup

1. **Clone the repo**

   ```bash
   git clone https://github.com/twisha/lumi-math-tutor.git
   cd lumi-math-tutor
   ```

2. **Install Python dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your Anthropic API key:

   ```env
   ANTHROPIC_API_KEY=your_api_key_here
   LUMI_MODEL=claude-haiku-4-5-20251001
   ```

   To use a different Claude model, change `LUMI_MODEL` (e.g. `claude-sonnet-4-6`).

## Running the App

```bash
export $(cat .env | xargs) && streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser and click **Start Session with Lumi!**

> **Note:** A Chainlit + LangSmith version (`chainlit_app.py`) is available on the `feature/improvements` branch. It requires Python 3.12 or earlier due to a Chainlit compatibility issue with Python 3.14.

## Project Structure

```text
lumi-math-tutor/
├── app.py                # Streamlit UI
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
├── core/
│   ├── prompts.py        # Lumi's system prompt and persona
│   ├── tutor_brain.py    # Agentic loop (Claude API + tool calls)
│   ├── tools.py          # Pure Python tool implementations
│   ├── mcp_server.py     # MCP server exposing tools over stdio
│   ├── mcp_bridge.py     # MCP client → Anthropic/OpenAI tool format bridge
│   ├── speech_input.py   # Mic recording + Whisper transcription
│   └── speech_output.py  # pyttsx3 text-to-speech
```

## Usage

| Input method | How |
| --- | --- |
| Voice | Click **Tap to Talk!**, speak for up to 5 seconds |
| Text | Type in the text box and click **Send** |
| New session | Click **New Session** in the sidebar |
| Debug tools | Toggle **Show tool calls** in the sidebar |
