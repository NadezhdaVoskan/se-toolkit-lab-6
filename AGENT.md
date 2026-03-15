# Agent Architecture

## Overview

The agent is a documentation assistant that uses LLM with tool calling to answer questions about the project. It implements an agentic loop where the LLM can call tools to gather information before providing final answers.

## LLM Provider

- **Provider**: Qwen Code API (OpenAI-compatible)
- **Model**: qwen3-coder-plus
- **Configuration**: Environment variables from `.env.agent.secret` (or inherited shell env)
  - `LLM_API_KEY`: API key for the LLM provider
  - `LLM_API_BASE`: Base URL for the OpenAI-compatible endpoint
  - `LLM_MODEL`: Model name for the chat completions API

## Backend API Authentication

The agent separates LLM access from backend API access:

- `LMS_API_KEY`: Used for authenticating requests to the running backend (the system under test).
- `AGENT_API_BASE_URL`: Base URL of the backend API (defaults to `http://localhost:42002`).

This separation ensures that the agent does not accidentally expose backend credentials to the LLM provider, and it models how production agents should safely call internal services.

## Tools

### read_file

- **Purpose**: Read file contents from the project repository
- **Parameters**: path (string) - relative path from project root
- **Security**: Prevents directory traversal (no '..' allowed)
- **Returns**: File contents or error message

### list_files

- **Purpose**: List files and directories at given path
- **Parameters**: path (string) - relative directory path from project root
- **Security**: Same traversal protection as read_file
- **Returns**: Newline-separated listing of entries

### query_api

- **Purpose**: Call the running backend API to retrieve live system state and runtime data.
- **Parameters**:
  - `method` (string): HTTP method (GET, POST, etc.)
  - `path` (string): API path (e.g., `/items/count`)
  - `body` (string, optional): JSON request body
- **Authentication**: Uses `LMS_API_KEY` via `Authorization: Bearer <LMS_API_KEY>`
- **Returns**: JSON string containing `status_code` and `body`

## Agentic Loop

1. Initialize with system prompt and user question
2. Send messages to LLM with tool schemas
3. If LLM requests tool calls, execute them sequentially
4. Add tool results back to conversation
5. Repeat until LLM provides final answer
6. Limit: Maximum 10 tool calls per question

## System Prompt Strategy

- Instructs LLM to use tools for wiki/ information
- Requests structured output with answer and source
- Emphasizes accuracy and tool usage efficiency

## Output Format

```json
{
  "answer": "Final response text",
  "source": "wiki/section.md#subsection",
  "tool_calls": [
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "file contents..."
    }
  ]
}
```

## Running the Agent

```bash
uv run agent.py "How do you resolve a merge conflict?"
```

## Security

- Path validation prevents access outside project directory
- All file operations use absolute paths with project root
- Error handling for missing files/directories

## Lessons Learned and Evaluation Workflow

This agent demonstrates a core pattern for building a "system agent":

1. **Tool separation**: Keep documentation lookups and runtime data queries separate, with different auth and trust levels.
2. **Agentic loop**: Let the model ask for tools as needed instead of forcing one-shot answers.
3. **Robustness**: Handle null/missing LLM responses, malformed JSON, and transient API failures.

When evaluating the agent, run the `run_eval.py` benchmark suite, which tests:

- Documentation lookup questions (wiki/source code) using `read_file`/`list_files`
- Runtime questions using `query_api`
- Multi-step debugging scenarios where the agent must combine API output and source inspection

These benchmarks help detect common failure modes: missing tool calls, wrong source attribution, and unsafe path access.

