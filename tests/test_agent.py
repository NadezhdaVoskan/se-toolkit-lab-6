import json
import subprocess
import pytest

def test_agent_output():
    """Test that agent.py outputs valid JSON with answer and tool_calls."""
    result = subprocess.run(
        ["uv", "run", "agent.py", "What is 2+2?"],
        capture_output=True,
        text=True,
        cwd="d:\\software-engineering-toolkit\\se-toolkit-lab-6"
    )
    assert result.returncode == 0, f"Agent failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "answer" in data
    assert "tool_calls" in data
    assert isinstance(data["tool_calls"], list)
    assert len(data["answer"]) > 0  # Ensure answer is not empty

def test_agent_merge_conflict():
    """Test agent uses read_file tool for merge conflict question."""
    result = subprocess.run(
        ["uv", "run", "agent.py", "How do you resolve a merge conflict?"],
        capture_output=True,
        text=True,
        cwd="d:\\software-engineering-toolkit\\se-toolkit-lab-6"
    )
    assert result.returncode == 0, f"Agent failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "answer" in data
    assert "source" in data
    assert "tool_calls" in data
    assert isinstance(data["tool_calls"], list)
    # Check that read_file was called
    read_file_calls = [call for call in data["tool_calls"] if call["tool"] == "read_file"]
    assert len(read_file_calls) > 0, "Expected read_file tool call"
    # Check source contains git-workflow
    assert "git-workflow" in data["source"]

def test_agent_list_files():
    """Test agent uses list_files tool for directory listing question."""
    result = subprocess.run(
        ["uv", "run", "agent.py", "What files are in the wiki?"],
        capture_output=True,
        text=True,
        cwd="d:\\software-engineering-toolkit\\se-toolkit-lab-6"
    )
    assert result.returncode == 0, f"Agent failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert "answer" in data
    assert "source" in data
    assert "tool_calls" in data
    assert isinstance(data["tool_calls"], list)
    # Check that list_files was called
    list_calls = [call for call in data["tool_calls"] if call["tool"] == "list_files"]
    assert len(list_calls) > 0, "Expected list_files tool call"