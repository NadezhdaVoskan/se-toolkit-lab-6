# Task 1: Call an LLM from Code - Implementation Plan

## LLM Provider and Model

- **Provider**: Qwen Code API (OpenAI-compatible proxy)
- **Model**: qwen3-coder
- **Reason**: Chosen by user, provides free access, available in Russia, and integrates well with the lab setup.

## Agent Structure

- **Language**: Python
- **Library**: openai (for API calls)
- **Input**: Command-line argument (question string)
- **Output**: JSON with "answer" and "tool_calls" fields
- **Configuration**: Read from environment variables:
  - LLM_API_KEY
  - LLM_API_BASE
  - LLM_MODEL
- **Error Handling**: Basic try-except for API calls
- **Security**: API key stored in .env.agent.secret, loaded via python-dotenv

## Implementation Steps

1. Create agent.py with CLI interface
2. Add openai dependency to pyproject.toml
3. Implement LLM call with system prompt
4. Output structured JSON response
5. Create AGENT.md documentation
6. Write regression test

## Testing

- Manual: Run `uv run agent.py "test question"` and verify JSON output
- Automated: Subprocess test checking JSON structure
