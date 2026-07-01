# Lumi Math Tutor — AI System Reliability Assessment

Assessed against the AI System Reliability Framework (ten dimensions).
Findings are derived from the actual code, config, and logs — not from the
README's description of intended behavior.

- **Date:** 2026-06-30
- **Commit context:** `main` @ 6a5bf90 ("Add misconception-aware Socratic tutoring")
- **System:** Voice/text AI math tutor for K–5, Claude (Haiku default) + MCP tools + Streamlit + LangSmith

---

## Tracker

| Dimension | Status | Notes / Evidence |
|---|---|---|
| 1. Determinism vs. Model Variance | Partial | Math is tool-verified & deterministic; orchestration hardcoded; but no `temperature` set (defaults to 1.0) and tutoring text is model-generated |
| 2. Confidence Signal Integrity | Partial | No confidence scores anywhere — none are fake, but `classify_misconception` silently degrades to `unknown_error` with no confidence signal |
| 3. Human-in-the-Loop Coverage | Gap | Teacher dashboard is passive reporting only; no review queue, no alerting; "reveal answer after 3 tries" is prompt-only |
| 4. Auditability & Traceability | Partial | LangSmith traces tool calls/latency/tokens/model; but no prompt versioning and transcripts live only in-memory |
| 5. Failure Mode Coverage | Partial → **improved** | API + speech + tool errors handled; agentic loop now has a `_MAX_TOOL_ITERATIONS` ceiling with a safe fallback |
| 6. Multi-Tenancy & Data Isolation | Gap → **fixed** | `conversation_history` was a module-level global shared across all concurrent Streamlit users; now threaded through `st.session_state` |
| 7. Evaluation & Regression Testing | Partial | Real eval suite + LLM-judge exists; but not wired to CI, and eval stub omits `classify_misconception` (tests a different toolset than prod) |
| 8. Cost & Latency Predictability | Partial → **improved** | `max_tokens=300` + prompt caching + tool-loop ceiling now set; `conversation_history` still grows unbounded within a session |
| 9. Security & Data Handling | Gap → **partially fixed** | `lumi_data.db` (child names + error data) was not git-ignored — now ignored; child PII still sent to Anthropic + LangSmith with no documented DPA/COPPA handling |
| 10. Adaptation Mechanism Fit | Partial | Math correctness correctly tool-enforced; but grade guardrails & no-spoiler are advisory (prompt + info-only tools), not hard-enforced |

---

## Dimension detail

### 1. Determinism vs. Model Variance — Partial
- **Deterministic (good):** arithmetic via a restricted AST evaluator (`core/tools.py:14` `_safe_eval`), `check_answer`, and `classify_misconception` (rule-based, `core/tools.py:200`). Orchestration/agentic loop is hardcoded in `core/tutor_brain.py`, not delegated to the LLM. `tool_choice` is forced to `"any"` when the child types a bare number (`core/tutor_brain.py:61`).
- **Variance (accepted/relaxed):** `client.messages.create()` sets no `temperature`, so it defaults to 1.0; all tutoring prose is model-generated. `generate_problem` is intentionally random.
- **Recommendation:** set an explicit `temperature` (e.g. 0.3–0.7) to bound tone variance; document that prose variance is intentional and math variance is not.

### 2. Confidence Signal Integrity — Partial
- No confidence scores exist anywhere in the pipeline. Notably there are **no** hardcoded `0.99`-style placeholders — a clean result for this dimension.
- `classify_misconception` returns a categorical match or silently falls back to `unknown_error` (`core/tools.py:233`) with no confidence; a misclassified error pattern produces a confident-sounding wrong hint.
- **Recommendation:** treat the misconception match as low/high based on how many heuristics fired; consider logging near-miss classifications.

### 3. Human-in-the-Loop Coverage — Gap
- The only human surface is the passive "Teacher View" sidebar (`app.py:412`) that reports recorded misconceptions. It is populated but not actively monitored or alerted on.
- No path routes a turn to a human. The pedagogical safety rule ("reveal the answer only after 3 wrong attempts") is enforced **only** by the system prompt (`core/prompts.py:42`), not by code.
- No silent error swallowing in the brain — tool exceptions return an error JSON to the model (`core/tutor_brain.py:107-110`) and API errors return friendly messages. But these are not logged anywhere durable.
- **Recommendation:** if HITL is in scope for the product, add a flag/queue for repeated failures or guardrail trips; at minimum, log guardrail events.

### 4. Auditability & Traceability — Partial
- **Strong:** `@traceable` + `wrap_anthropic` (`core/tutor_brain.py:22,55`) trace every turn with tool calls, latency, tokens, and the model id. The debug panel surfaces per-turn tool args/results (`app.py`).
- **Gaps:** system prompts are bare string literals (`core/prompts.py`) with no version id, so prompt drift is invisible in traces. Full transcripts live only in memory (`conversation_history`) and are lost on reset; only misconceptions persist (SQLite).
- **Recommendation:** add a prompt-version constant and attach it as trace metadata.

### 5. Failure Mode Coverage — Partial
- Handled: `AuthenticationError`, `RateLimitError`, generic `APIError` (`core/tutor_brain.py:77-85`), per-tool exceptions (`:107`), MCP call timeout 30s (`core/mcp_bridge.py:23`), Whisper empty transcription and mic-silence (`app.py:283,290`), audio device fallback (`core/speech_input.py:100`).
- **Fixed:** the loop now runs at most `_MAX_TOOL_ITERATIONS` (6) round-trips (`core/tutor_brain.py`); on exhaustion it returns a safe in-character fallback instead of looping forever, and leaves history in a valid state for the next turn.
- **Remaining:** MCP session is not re-established if the subprocess dies mid-session.

### 6. Multi-Tenancy & Data Isolation — Gap → fixed
- **Original defect:** `conversation_history` was a module-level global (`core/tutor_brain.py:24`). Streamlit serves all browser sessions from one process, so concurrent students shared one conversation buffer — turns/answers leaked between children. The team already knew (evals pin `max_concurrency=1` with the comment "conversation_history is a global — concurrent runs corrupt it", `evals/run_langsmith_evals.py:153`).
- **Fix applied:** `ask_lumi` / `reset_conversation` now take an optional per-session `history`; `app.py` passes `st.session_state.conversation_history`. The module global remains only as a fallback for single-threaded eval/test callers.
- **Remaining:** `student_id` defaults to `"anonymous"`, which collides across un-named students in SQLite; no access control on the DB.

### 7. Evaluation & Regression Testing — Partial
- A real suite exists: pytest tests (`evals/test_*.py`), a LangSmith batch runner (`evals/run_langsmith_evals.py`), golden cases (`evals/dataset.py`), deterministic evaluators, and an LLM-as-judge no-spoiler check (`evals/evaluators.py:53`). Metrics are domain-relevant (tool compliance, no-spoiler, redirect, response length).
- **Fidelity gap:** the eval stub `_FN_MAP` / `_TOOLS_ANTHROPIC` omit `classify_misconception` (`evals/_stub.py:16`), even though it is a production tool (`core/mcp_server.py:89`) and the basis of the headline misconception-hint feature. In evals the model cannot call it, so that feature is untested; if it tried, it would get `"Unknown tool"`.
- No CI gate runs evals before prompt/model changes.
- **Recommendation:** mirror the full prod toolset in the stub; add a CI step that runs the deterministic evals on PRs.

### 8. Cost & Latency Predictability — Partial
- Set explicitly: `max_tokens=300` (`core/tutor_brain.py`), system-prompt caching via `cache_control` (`:68-72`), MCP 30s timeout.
- **Gaps:** unbounded agentic loop (see Dim 5) is also a runaway-cost path. `conversation_history` is never trimmed within a session, so token cost grows every turn. No per-session budget; no worst-case cost/latency estimate documented.
- **Recommendation:** cap loop iterations; window or summarize history; document a worst-case single-request cost.

### 9. Security & Data Handling — Gap → partially fixed
- **Fixed:** `lumi_data.db` (student names + per-student error history) was untracked and absent from `.gitignore`; a `git add .` would have committed children's data. Now git-ignored.
- **Strong:** `.env` is git-ignored; API keys are read from env and not logged; `calculate` uses a restricted AST evaluator (no `eval` injection).
- **Remaining:** child names flow to Anthropic (conversation) and LangSmith (traces) with no redaction and no documented data-processing / COPPA posture for an under-13 audience. Prompt-injection defense for child input is prompt-only ("Absolute Rules", `core/prompts.py:105`).
- **Recommendation:** pseudonymize/hash `student_id` before persistence and tracing; document the third-party data path and lawful basis.

### 10. Adaptation Mechanism Fit — Partial
- **Right mechanism:** the hard constraint "never output wrong math" is tool-enforced (`calculate`/`check_answer`) — the correct, highest-reliability choice.
- **Mismatch:** grade guardrails (`check_grade_level`) and topic redirects (`check_topic`) only *return information*; the model decides whether to comply, so "K-2 blocks multiplication" is advisory, not enforced. Keyword sets (`core/tools.py:34-45`) are easily evaded by rephrasing. The no-spoiler rule is prompt-only (validated in evals but not enforced at runtime).
- **Recommendation:** if grade-scoping is a hard requirement, gate the response in code on the `check_grade_level` result rather than trusting prompt compliance; document each mechanism choice.

---

## Remediation status

| Item | Severity | Status |
|---|---|---|
| Cross-session `conversation_history` leak (Dim 6) | High | **Fixed** — threaded through `st.session_state` |
| `lumi_data.db` PII not git-ignored (Dim 9) | High | **Fixed** — added to `.gitignore` |
| Unbounded agentic loop (Dim 5, 8) | Medium | **Fixed** — `_MAX_TOOL_ITERATIONS` cap + safe fallback |
| Unbounded `conversation_history` growth (Dim 8) | Medium | Open |
| Eval stub omits `classify_misconception` + no CI (Dim 7) | Medium | Open |
| Guardrails advisory, not enforced (Dim 10) | Medium | Open |
| Prompt versioning absent (Dim 4) | Low | Open |
| `temperature` not set (Dim 1) | Low | Open |
| Child PII to third parties undocumented (Dim 9) | Medium | Open |
