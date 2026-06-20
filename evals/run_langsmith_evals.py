"""
LangSmith batch eval runner for Lumi.

Creates (or reuses) a dataset in LangSmith and runs all evaluators,
logging scores as an experiment you can compare over time.

Prerequisites:
  export LANGCHAIN_API_KEY=<your key>
  export LANGCHAIN_TRACING_V2=true
  export ANTHROPIC_API_KEY=<your key>

Run from the project root:
  python -m evals.run_langsmith_evals
"""
# _stub must be imported first — patches core.mcp_bridge before tutor_brain loads
import evals._stub  # noqa: F401

from core.tutor_brain import ask_lumi, reset_conversation
from evals.dataset import TOOL_COMPLIANCE_CASES, NO_SPOILER_CASES, GUARDRAIL_CASES
from evals.evaluators import (
    ls_tool_compliance,
    ls_response_length,
    ls_no_spoiler,
    ls_redirects_to_math,
)

from langsmith import Client
from langsmith.evaluation import evaluate

DATASET_NAME = "lumi-tutor-evals"

# ── Build the unified example list ───────────────────────────────────────────

def _build_examples() -> list[dict]:
    examples = []

    for desc, setup_input, user_input, grade, required_tools in TOOL_COMPLIANCE_CASES:
        examples.append({
            "inputs": {"user_input": user_input, "grade": grade, "setup_input": setup_input},
            "outputs": {
                "required_tools": list(required_tools),
                "user_input": user_input,
                "answer": None,
                "should_redirect": None,
            },
            "metadata": {"category": "tool_compliance", "description": desc},
        })

    for desc, user_input, grade, answer in NO_SPOILER_CASES:
        examples.append({
            "inputs": {"user_input": user_input, "grade": grade},
            "outputs": {
                "required_tools": [],
                "user_input": user_input,
                "answer": answer,
                "should_redirect": None,
            },
            "metadata": {"category": "no_spoiler", "description": desc},
        })

    for desc, user_input, grade, should_redirect in GUARDRAIL_CASES:
        examples.append({
            "inputs": {"user_input": user_input, "grade": grade},
            "outputs": {
                "required_tools": [],
                "user_input": user_input,
                "answer": None,
                "should_redirect": should_redirect,
            },
            "metadata": {"category": "guardrail", "description": desc},
        })

    return examples


# ── Dataset setup ─────────────────────────────────────────────────────────────

def _get_or_create_dataset(client: Client) -> str:
    """Delete and recreate the dataset so it always matches the current cases."""
    existing = [d for d in client.list_datasets() if d.name == DATASET_NAME]
    if existing:
        print(f"Deleting stale dataset '{DATASET_NAME}' to sync with current cases ...")
        client.delete_dataset(dataset_id=existing[0].id)

    print(f"Creating dataset '{DATASET_NAME}' ...")
    examples = _build_examples()
    dataset = client.create_dataset(DATASET_NAME, description="Lumi math tutor golden eval cases")
    client.create_examples(
        inputs=[e["inputs"] for e in examples],
        outputs=[e["outputs"] for e in examples],
        metadata=[e["metadata"] for e in examples],
        dataset_id=dataset.id,
    )
    print(f"  Created {len(examples)} examples.")
    return dataset.id


# ── Target function ───────────────────────────────────────────────────────────

def run_lumi(inputs: dict) -> dict:
    reset_conversation()
    if inputs.get("setup_input"):
        ask_lumi(inputs["setup_input"], grade_group=inputs["grade"])
    reply, tool_log, _ = ask_lumi(inputs["user_input"], grade_group=inputs["grade"])
    return {"reply": reply, "tool_log": tool_log}


# ── Evaluator routing ─────────────────────────────────────────────────────────
# Each evaluator gracefully skips cases where it doesn't apply
# (e.g. ls_tool_compliance skips no-spoiler rows that have no required_tools).

def eval_tool_compliance(outputs: dict, reference_outputs: dict) -> dict:
    if not reference_outputs.get("required_tools"):
        return {"key": "tool_compliance", "comment": "n/a"}
    return ls_tool_compliance(outputs, reference_outputs)


def eval_no_spoiler(outputs: dict, reference_outputs: dict) -> dict:
    if not reference_outputs.get("answer"):
        return {"key": "no_spoiler", "comment": "n/a"}
    return ls_no_spoiler(outputs, reference_outputs)


def eval_redirect(outputs: dict, reference_outputs: dict) -> dict:
    if reference_outputs.get("should_redirect") is None:
        return {"key": "redirect_to_math", "comment": "n/a"}
    if not reference_outputs["should_redirect"]:
        return {"key": "redirect_to_math", "comment": "in-scope — redirect not expected"}
    return ls_redirects_to_math(outputs, reference_outputs)


def eval_response_length(outputs: dict, reference_outputs: dict) -> dict:
    return ls_response_length(outputs, reference_outputs)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    client = Client()
    dataset_id = _get_or_create_dataset(client)

    print("\nRunning evals ...")
    results = evaluate(
        run_lumi,
        data=DATASET_NAME,
        evaluators=[
            eval_tool_compliance,
            eval_no_spoiler,
            eval_redirect,
            eval_response_length,
        ],
        experiment_prefix="lumi",
        max_concurrency=1,  # conversation_history is a global — concurrent runs corrupt it
    )

    print(f"\nExperiment URL: {results.experiment_name}")
    print("Done. Open LangSmith to view scores per example.")
