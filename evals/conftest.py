"""
Pytest configuration for Lumi evals.

_stub must be the first import — it installs the MCP bridge mock into
sys.modules before tutor_brain (imported by test files) can trigger the
real subprocess connection.
"""
import evals._stub  # noqa: F401  — side-effect import, must be first

import pytest


@pytest.fixture(autouse=True)
def reset_lumi():
    from core.tutor_brain import reset_conversation
    reset_conversation()
    yield
    reset_conversation()
