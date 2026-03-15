# Agent Architecture

## Workflow note

This PR ensures the task follows the required Git workflow.

## Overview

The agent is a command-line tool that calls an LLM to answer questions and returns structured JSON responses.

## LLM Provider

- **Provider**: Qwen Code API (OpenAI-compatible)
- **Model**: qwen3-coder
- **Configuration**: Environment variables from .env.agent.secret
  - `LLM_API_KEY`: API key for authentication
  - `LLM_API_BASE`: Base URL for the API endpoint
  - `LLM_MODEL`: Model name to use

## How It Works

1. Takes a question as command-line argument
2. Loads LLM configuration from environment
3. Calls the OpenAI-compatible API
4. Returns JSON with `answer` and `tool_calls` fields

## Running the Agent

```bash
uv run agent.py "Your question here"
```

Example output:

```json
{
  "answer": "The answer to your question",
  "tool_calls": []
}
```

## Architecture

- **Language**: Python
- **Dependencies**: openai, python-dotenv
- **Error Handling**: Basic exception handling for API calls
- **Security**: API key stored securely in .env.agent.secret
