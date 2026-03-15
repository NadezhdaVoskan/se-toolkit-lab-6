# Task 2: The Documentation Agent - Implementation Plan

## Overview
Extend the agent from Task 1 to support tool calling with read_file and list_files tools. Implement an agentic loop where the LLM can call tools iteratively to gather information before providing a final answer.

## Tool Definitions
- **read_file**: Reads file contents from project repository
  - Parameter: path (string) - relative path from project root
  - Security: Validate path doesn't contain '..' to prevent directory traversal
  - Return: File contents or error message

- **list_files**: Lists files and directories at given path
  - Parameter: path (string) - relative directory path from project root
  - Security: Same path validation as read_file
  - Return: Newline-separated listing

## Agentic Loop Implementation
1. Send initial user question to LLM with tool schemas
2. If LLM responds with tool calls, execute them sequentially
3. Add tool results as assistant messages
4. Repeat until LLM provides final answer (no more tool calls)
5. Limit to maximum 10 tool calls per question
6. Parse final response for answer and source

## System Prompt Strategy
- Minimal system prompt focusing on documentation assistance
- Instruct LLM to use tools to find information in wiki/
- Request source citation in specific format
- Encourage efficient tool usage

## Output Structure
- answer: Final response text
- source: Wiki section reference (e.g., wiki/git-workflow.md#resolving-merge-conflicts)
- tool_calls: Array of all executed tool calls with tool, args, result

## Security Measures
- Path validation: Reject any path containing '..'
- Absolute path construction using os.path.join with project root
- File existence checks before reading

## Testing
- Test tool calling with specific questions
- Verify path security (attempt ../ should fail)
- Check output format and source accuracy
- Regression tests for both tools

## Implementation Steps
1. Define tool schemas as per OpenAI function calling format
2. Implement tool execution functions with security
3. Build agentic loop with message history
4. Update output parsing for source and tool_calls
5. Add comprehensive error handling
6. Write tests and documentation