import io
import json
import os
import sys
from contextlib import redirect_stdout, redirect_stderr

import pytest

import agent


def _run_agent(question):
    """Run the agent main() with a mock LLM and return parsed JSON output."""
    old_env = os.environ.copy()
    os.environ.update({
        "LLM_API_KEY": "mock",
        "LLM_API_BASE": "mock",
        "LLM_MODEL": "mock",
        "LMS_API_KEY": "mock",
        "AGENT_API_BASE_URL": "mock",
    })

    old_argv = sys.argv
    try:
        sys.argv = ["agent.py", question]
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                agent.main()
            except SystemExit as e:
                if e.code != 0:
                    raise
        return json.loads(stdout.getvalue())
    finally:
        sys.argv = old_argv
        os.environ.clear()
        os.environ.update(old_env)


def test_agent_output():
    """Test that agent outputs valid JSON with answer and tool_calls."""
    data = _run_agent("What is 2+2?")
    assert "answer" in data
    assert "tool_calls" in data
    assert isinstance(data["tool_calls"], list)
    assert len(data["answer"]) > 0


def test_agent_framework_detection():
    """Test that the agent uses read_file when asked about the backend framework."""
    data = _run_agent("What framework does the backend use?")
    assert "tool_calls" in data
    read_file_calls = [c for c in data["tool_calls"] if c["tool"] == "read_file"]
    assert len(read_file_calls) > 0


def test_agent_items_count_calls_query_api():
    """Test that the agent uses query_api when asked about database item count."""
    data = _run_agent("How many items are in the database?")
    assert "tool_calls" in data
    query_calls = [c for c in data["tool_calls"] if c["tool"] == "query_api"]
    assert len(query_calls) > 0
