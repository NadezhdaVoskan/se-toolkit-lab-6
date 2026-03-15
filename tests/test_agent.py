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