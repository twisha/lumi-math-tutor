# Lumi — Step-by-Step Demo & Presentation Guide

---

## ✅ PRE-PRESENTATION CHECKLIST (do this 5 min before)

- [ ] Run: `export $(cat .env | xargs) && streamlit run app.py`
- [ ] Open **Browser Tab 1** → `presentation.html` (drag to full screen)
- [ ] Open **Browser Tab 2** → `http://localhost:8501`
- [ ] In Tab 2: Click **▶️ Start K–2 Session** so it's ready
- [ ] In Tab 2: Turn ON **"Show tool calls (debug)"** in the sidebar
- [ ] Set system volume to ~60% (Lumi will speak during demo)
- [ ] Close Slack, notifications, other apps

---

## SLIDE 1 — Title (30 sec)

**Tab 1 → presentation.html**

Say:
> "This is Lumi — a voice math tutor for young kids, built end to end for my capstone. It supports K through 2nd grade and Grade 3 through 5. I'll alternate between the slides and a live demo so you can see every concept working in real time."

➡️ Press **→** to advance

---

## SLIDE 2 — Problem → Solution (90 sec)

Say:
> "Young kids can't type — so traditional chat tutors don't work for them. Lumi gives them a full voice loop: speak, transcribe locally with Whisper, reason with Claude, verify the math with MCP tools, speak the answer back."

Point to each card as you speak:
- **Problem card** → "Can't type, hallucinated answers are dangerous for kids"
- **Solution card** → "Real agentic loop, end to end"
- **Two Grade Levels** → "Different system prompts, different teaching strategies"
- **Guardrails card** → "Every answer tool-verified — never guessed"

➡️ Press **→** to advance — then switch to the app

---

## 🟢 DEMO 1 — K-2 Basic Flow (3 min)

**Switch to Tab 2 (Lumi app)**

> "Let me show you the basic flow first."

### Step 1 — Start a session
- The K-2 session is already open
- Point out: **Lumi speaks the intro aloud**
- Point out: sidebar shows K-2 topics, guardrails active, voice ON

### Step 2 — Ask a math question
- Type in the text box: **`What is 6 plus 8?`** → Send
- Say: *"Lumi calls calculate() first — notice the tool trace below the message"*
- **Point to tool trace:** `calculate("6+8") = 14`
- Lumi asks: *"What do you think?"* — **it does NOT give the answer**

### Step 3 — Give a wrong answer
- Type: **`20`** → Send
- **Point to tool trace:** `check_answer(expected=14, given=20) → correct: false`
- Lumi gives a hint — **visual helper appears** (hop-path with ★9 → 10 → 11 → 12 → 13 → ?)
- Say: *"Visual only appears when the child is wrong or asks for help — not on the first question"*

### Step 4 — Give the right answer
- Type: **`14`** → Send
- **Point to tool trace:** `check_answer(expected=14, given=14) → correct: true`
- Lumi celebrates

> "Three things to notice: Lumi never guessed the answer. The visual only appeared after a wrong attempt. And every step is traced — calculate, check_answer, all of it."

**Switch back to Tab 1**

---

## SLIDE 3 — Architecture (90 sec)

Say (pointing to each row of the flow diagram):
> "Row 1: Child speaks → Whisper transcribes locally → tutor_brain sends to Claude.
>
> Row 2: Claude calls tools via MCP. The bridge translates between MCP's stdio protocol and Anthropic's SDK format. The tools — calculate, check_answer, generate_problem — run as a local subprocess.
>
> Row 3: The reply comes back with an optional self-tag. visual_aids.py decides whether to render a hop-path. macOS say speaks it aloud.
>
> And LangSmith traces every conversation turn — I have full observability."

➡️ Press **→** to advance

---

## SLIDE 4 — AI Concepts (2 min)

Walk through all 6 cards — spend ~20 sec each:

**Prompt Engineering:**
> "Two separate system prompts — K-2 and Grade 3-5 — each encoding a full teaching strategy. Hint escalation, visual references, guardrails — all in natural language. Zero fine-tuning."

**Agentic Tool Use:**
> "Claude autonomously picks which tool to call. I don't hardcode 'if math question → calculate'. Claude reasons about it."

**MCP Protocol:**
> "The tools run as a real MCP server over stdio. Completely swappable — change the model, keep the tools."

**LLM Self-Tagging** ← spend extra time here:
> "This is my favourite part. When Lumi asks a child to count from 1 to 20, I need a 23-second recording window. Instead of writing regex to detect counting questions, I told Lumi: 'If you're asking the child to count out loud, append [COUNT:N] to your response.' The app strips the tag and computes duration as N plus 3 seconds. The model classifies its own intent. No rules. No regex. I'll show this live next."

**Prompt Caching:**
> "The system prompt is marked ephemeral on every API call. Saves latency and tokens on every turn."

**Multimodal I/O:**
> "Whisper locally — child's voice never leaves the device. Silence detection stops recording as soon as the child stops speaking. macOS say with a trailing 500ms buffer so the last word isn't clipped."

➡️ Press **→** to advance — then switch to the app

---

## 🟢 DEMO 2 — LLM Self-Tagging + Counting (2 min)

**Switch to Tab 2 (Lumi app) — start a NEW K-2 session**

> "Let me show you LLM self-tagging in action."

### Step 1 — Ask for counting
- Type: **`I would like to practice counting`** → Send
- Lumi responds with a counting challenge
- **Point to the button label:** it shows **"8 sec · auto-stops"** or **"13 sec · auto-stops"**
- Say: *"That number comes from the [COUNT:N] tag Lumi embedded in its reply. I'll show you."*
- **Point to the tool trace** — no COUNT tag on this one if it's a single-answer question

### Step 2 — Trigger a longer count
- Type: **`Can you ask me to count to 15?`** → Send
- Lumi responds with "Count from 1 to 15 for me!"
- **Point to button:** now shows **"18 sec · auto-stops"** (15 + 3)
- Say: *"18 seconds — automatically computed from [COUNT:15]. The model tagged its own output."*

### Step 3 — Show visual gating on word problems
- Type: **`Give me a word problem`** → Send
- Lumi gives a word problem — **no visual appears**
- Say: *"No visual — because this is the first presentation. The child hasn't struggled yet."*
- Type: **`I have no idea`** → Send
- **Visual appears now** — the hop-path for the underlying equation
- Say: *"Now the visual appears. The app detected 'I have no idea' as a help request and revealed it."*

**Switch back to Tab 1**

---

## SLIDE 5 — Visual Aids (90 sec)

Point to each card:

**Hop-Path:**
> "A traditional 0-20 number line has 21 tiny numbers. A 5-year-old can't read that. The hop-path shows only the relevant circles — large, connected by arrows. The ★ START is always the larger number, which is how count-on-from-larger works."

**Color-Blind Accessible:**
> "Color is never the only signal. The start circle is bigger, has a star, and says START. The answer has a dashed border and says YOU. Any child can follow it."

**Shown Only When Struggling:**
> "We just saw this — hidden on first presentation, appears on wrong answer or help request. Detected from the child's words and the check_answer tool result."

**Prompt ↔ Visual Alignment:**
> "Lumi's spoken hint and the visual teach the same strategy. Lumi says 'look at the START circle, hop along each circle'. The visual shows exactly that path. They reinforce each other."

➡️ Press **→** to advance — then switch to app for Demo 3

---

## 🟢 DEMO 3 — Grade 3-5 + Guardrails (2 min)

**Switch to Tab 2 — click "New Session" → Start Grade 3-5**

> "Let me quickly show Grade 3-5 and the guardrail system."

### Step 1 — Note the differences
- Point out: **Voice is OFF by default** (Grade 3-5 kids can type)
- Point out: **Sidebar topics** → multiplication, division, fractions
- Point out: **No visual helper** — Grade 3-5 doesn't use them

### Step 2 — Ask a Grade 3-5 question
- Type: **`What is 7 times 8?`** → Send
- **Point to tool trace:** `calculate("7*8") = 56`
- Give wrong answer: **`48`**
- **Point to trace:** `check_answer → false` — Lumi gives a strategic hint (no hop-path)

### Step 3 — Trigger the grade guardrail
- Type: **`What is the square root of 144?`** → Send
- **Point to tool trace:** `check_grade_level() → out of scope`
- Lumi redirects warmly — doesn't attempt to answer
- Say: *"Two-layer guardrail — the tool confirms it's out of scope, the system prompt handles the warm redirect. The child never feels bad about asking."*

**Switch back to Tab 1**

---

## SLIDE 6 — Demo Transcript (30 sec)

> "This slide mirrors what we just saw — the full agentic loop. Calculate fires silently. Child is wrong — check_answer fires. Visual appears. Child gets it. check_answer confirms. Every response is grounded by a tool. Lumi never guesses."

➡️ Press **→** to advance

---

## SLIDE 7 — Close (60 sec)

> "To close — this project demonstrates eight AI engineering fundamentals in one working product: prompt engineering, agentic tool use, MCP protocol, LLM self-tagging, prompt caching, multimodal I/O, guardrails, and observability.
>
> The stack is Claude Haiku, MCP over stdio, local Whisper, macOS say, Streamlit, LangSmith, and Python.
>
> The repo is at github.com/twisha/lumi-math-tutor. Happy to take questions."

---

## ❓ Q&A CHEAT SHEET

| Question | Answer |
|---|---|
| Why Haiku not Sonnet? | Speed matters for kids. Haiku with a strong prompt beats a slow Sonnet. |
| Why MCP not direct functions? | Model-agnostic, separately testable, industry standard. Swap the model, keep the tools. |
| Why local Whisper? | Child voice privacy — nothing leaves the device after model download. |
| Hardest bug? | Streamlit double-tap lock — queued widget events firing after recording ended. Fixed with unconditional reset + cooldown timestamp. |
| Why macOS say not a TTS API? | Same reason as Whisper — local, private, zero latency, no cost per character. |
| What would you add next? | Adaptive difficulty (track child's accuracy over sessions), parent dashboard via LangSmith traces, and a web deployment with WebRTC for cross-platform voice. |
| Did you use AI to write the code? | Yes — we used Claude Code as our development tool. The architecture, AI design decisions, prompt engineering, and tool design are ours. Claude Code accelerated the implementation the same way a senior pair programmer would. The product we built is what matters — and it works. |
