# Agent Architecture

## Overview
The agent is a documentation assistant that uses LLM with tool calling to answer questions about the project. It implements an agentic loop where the LLM can call tools to gather information before providing final answers.

## LLM Provider
- **Provider**: Qwen Code API (OpenAI-compatible)
- **Model**: qwen3-coder-plus
- **Configuration**: Environment variables from .env.agent.secret
  - `LLM_API_KEY`: API key for authentication
  - `LLM_API_BASE`: Base URL for the API endpoint
  - `LLM_MODEL`: Model name to use

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
