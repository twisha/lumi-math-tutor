# Lumi Math Tutor — Presentation Transcript & Demo Plan

---

## Execution Plan

| Step | Mode | Duration |
|------|------|----------|
| Slides 1–2 | Presentation | ~3 min |
| **Demo 1** | Live app — K-2 basic flow | ~3 min |
| Slides 3–4 | Presentation | ~4 min |
| **Demo 2** | Live app — visual aid + LLM self-tag | ~3 min |
| Slide 5 | Presentation | ~2 min |
| **Demo 3** | Live app — Grade 3-5 session | ~2 min |
| Slides 6–7 | Presentation | ~2 min |
| **Total** | | **~19 min** |

**Setup before presenting:**
- Browser window 1: `presentation.html` (open locally, full-screen)
- Browser window 2: `http://localhost:8501` (Lumi app, running)
- Switch between them with Cmd+Tab or side-by-side if dual monitor
- Start a fresh K-2 session in the app before you begin

---

## Slide 1 — Title

> "Today I'm going to walk you through Lumi — a voice-powered math tutor for young kids that I built from scratch as my capstone project.
>
> Lumi supports two grade levels: K through 2nd grade, and Grades 3 through 5. It listens to children speak, reasons with Claude, verifies every answer through tools, and talks back — all locally.
>
> What makes this interesting as an AI engineering project is that it isn't just a chatbot with a system prompt. It applies six real AI engineering fundamentals — and I'll show you each one both in the slides and in a live demo."

---

## Slide 2 — What We Built

> "Let's start with the problem. Young kids — ages 5 to 10 — can't type. They need to speak. Traditional chat tutors simply don't work for them.
>
> Lumi solves this with a full voice loop: the child speaks, Whisper transcribes it locally, Claude reasons about the response, MCP tools verify the math, and macOS TTS speaks the answer back. It's a real agentic loop from end to end.
>
> We support two very different grade levels. For K-2, we teach counting, addition, and subtraction within 20 — with visual hop-path aids that appear when a child is struggling. For Grade 3 through 5, we teach multiplication, division, fractions, and multi-step word problems.
>
> And crucially — every answer is tool-verified. Lumi never guesses at math."

---

## 🟢 DEMO 1 — K-2 Basic Flow (~3 min)

**Switch to the Lumi app.**

**What to show:**
1. Click **Start K–2 Session** — note the grade picker and intro message spoken aloud
2. Type or say: **"What is 6 plus 8?"**
3. Point out: Lumi asks the child to guess first — it doesn't give the answer
4. Type: **"14"** (wrong answer)
5. Show: visual helper appears with ★ START circle and hop path
6. Lumi's hint references the visual — "look at the START circle"
7. Type: **"13"** (wrong again)
8. Note: Lumi gives a second hint, not the answer yet
9. Type: **"14"** — Lumi confirms

**Say:**
> "Notice a few things. Lumi never just gives the answer — it's designed to guide the child to discover it. When the child struggles, a visual aid appears. And every time a child gives a number, Lumi calls the check_answer tool to verify it before responding. Let me show you what's happening under the hood — I'll turn on the debug panel."

**Turn on "Show tool calls" in the sidebar.**

---

## Slide 3 — Architecture

> "Here's the full system. The child speaks or types. Whisper transcribes it locally on the machine — no cloud calls for STT. tutor_brain.py sends that to Claude, which is where all the reasoning happens.
>
> When Claude needs to do math, it calls tools. Those tools run as a local MCP server over stdio — the same protocol used by Claude Code and other professional AI tooling. The bridge translates between MCP format and the Anthropic SDK format, so the tools are completely model-agnostic.
>
> The reply comes back with optional metadata — I'll explain that in a moment. It goes to visual_aids.py if a visual should be shown, and then to macOS TTS which speaks it aloud.
>
> And every single ask_lumi() call is traced in LangSmith, so I have full observability over the conversation."

---

## Slide 4 — AI Concepts

> "Let me walk through the six fundamentals this project demonstrates.
>
> **Prompt Engineering.** Lumi has two completely separate system prompts — one for K-2, one for Grade 3-5 — each encoding a different teaching strategy, hint escalation approach, and set of guardrails. No fine-tuning. Just well-structured natural language.
>
> **Agentic Tool Use.** Claude autonomously decides when to call which tool. It doesn't just answer — it reasons about whether to calculate, check the child's answer, generate a new problem, or classify the topic. The tools constrain its behavior without hardcoding logic in the app.
>
> **MCP Protocol.** The tools are a real MCP server running as a subprocess. This means they could be swapped for any other MCP-compatible tool server without changing the LLM layer.
>
> **LLM Self-Tagging** — this is the most interesting one. When Lumi asks a child to count out loud — say 'Count from 1 to 20 for me' — it needs 20+ seconds of recording time. Instead of writing regex to detect counting questions, I had Lumi tag its own output with [COUNT:20]. The app strips the tag and sets the recording window to 20 plus 3 seconds. The LLM classifies its own intent. I'll show this in the next demo.
>
> **Prompt Caching.** The system prompt is marked ephemeral in every API call. This cuts latency and token cost on multi-turn conversations — which is every conversation with a child.
>
> **Multimodal I/O.** Whisper for speech-to-text with silence detection — it stops recording as soon as the child stops speaking, rather than waiting a fixed duration. macOS say for TTS with Unicode normalization and a trailing silence buffer to prevent the last word from being cut off."

---

## 🟢 DEMO 2 — LLM Self-Tagging + Visual Aid (~3 min)

**Stay in the K-2 session (or start fresh).**

**What to show:**
1. Say: **"I would like to learn counting"**
2. Lumi responds — point out the button shows **"8 sec"** or **"13 sec"** (self-tagged)
3. Say: **"Count from 1 to 10 for me"** — point out the recording window matches
4. Then ask a word problem: **"Give me a simple word problem"**
5. Lumi gives one — no visual shown yet
6. Type: **"I don't know"**
7. Show: visual appears now with the hop-path for the underlying equation
8. Show the tool trace — check_answer called, show_visual triggered

**Say:**
> "See how the recording window changed? That's the [COUNT:N] tag at work. Lumi decided it was a counting task and embedded the count directly in its response. No regex. No hardcoded rules. The model classifies its own output.
>
> And the visual — it only appeared when the child said they didn't know. On the first presentation of the word problem, there's no visual. The app gates it on the child's struggle state."

---

## Slide 5 — Visual Aids

> "Let me explain the visual design choices, because they weren't obvious.
>
> The first instinct was a traditional 0 to 20 number line. But 21 numbers squeezed into a row is unreadable for a 5-year-old. So I replaced it with a hop-path — just the relevant circles, large enough to tap, connected by arrows.
>
> The teaching strategy matters too. We use count-on-from-larger — start at the bigger number and count up. So for 4 plus 9, you start at 9, not at 1. The ★ START circle is always the larger operand.
>
> The answer position is intentionally left as a '?' — the child has to land on it, not be told it. The visual teaches the strategy without giving the answer away.
>
> And every visual cue is redundant for color blindness. Color alone is never the signal. The start is bigger, has a star, and says START. The answer has a dashed border and says YOU. Any child can follow it."

---

## 🟢 DEMO 3 — Grade 3-5 Session (~2 min)

**Click "New Session" in sidebar, start Grade 3-5.**

**What to show:**
1. Note: Voice is OFF by default for Grade 3-5 (can type)
2. Note: No visual helper in 3-5 — sidebar shows different topics
3. Ask: **"What is 7 times 8?"**
4. Give wrong answer, show hint escalation
5. Ask an out-of-scope question: **"What is 15% of 80?"**
6. Show guardrail redirect

**Say:**
> "Grade 3-5 is a different experience. Voice is optional since older kids can type comfortably. The topics are multiplication, division, fractions. And the guardrail is tuned differently — percentages are out of scope for Grade 3-5, so Lumi redirects warmly rather than attempting to answer."

---

## Slide 6 — Demo Slide

> "The demo slide shows the full agentic loop in one conversation. The child asks a question. Claude calls calculate silently. Asks the child to try. Child is wrong — check_answer fires. Lumi gives a hint referencing the visual. Child gets it right. check_answer confirms. Lumi celebrates.
>
> Every response is grounded by a tool call. Lumi never guesses."

---

## Slide 7 — Close

> "To recap what this project demonstrates as an AI engineering exercise:
>
> Prompt engineering — two grade-level personas in pure natural language. Agentic tool use — Claude drives its own tool calls. MCP protocol — a real stdio server, not mocked functions. LLM self-tagging — the model annotates its own output to drive app behavior. Prompt caching — cost and latency optimization built in from day one. Multimodal I/O with silence detection and TTS robustness.
>
> The stack is Claude Haiku, MCP over stdio, Whisper locally, macOS say for TTS, Streamlit for the UI, and LangSmith for observability.
>
> The repo is at github.com/twisha/lumi-math-tutor. Happy to take questions."

---

## Q&A Prep

**"Why Claude Haiku and not a bigger model?"**
> Haiku is fast and cheap — critical for a child-facing app where latency kills the experience. The heavy lifting is in the system prompt and tools, not model size. Haiku handles it well.

**"Why MCP instead of just calling functions directly?"**
> MCP makes the tools model-agnostic and separately testable. I can swap Claude for any MCP-compatible LLM without touching the tool layer. It's also the protocol the industry is converging on.

**"Why not use a speech API instead of local Whisper?"**
> Privacy — a child's voice shouldn't leave the device. Local Whisper runs on-machine with no cloud dependency after model download.

**"What's the hardest bug you fixed?"**
> The double-tap recording lock in Streamlit. Streamlit queues widget events — a second tap while recording would fire after the recording ended, re-triggering it. Fixed with an unconditional reset at script start and a 2-second cooldown timestamp.
