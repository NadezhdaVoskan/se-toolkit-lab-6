# Task 3: The System Agent - Implementation Plan

## Goal
Extend the documentation agent to become a system agent that can:
- Read documentation and source files
- Query the running backend API
- Combine both sources to answer questions about system behavior

## New Tool: `query_api`
### Schema
- **name**: `query_api`
- **description**: "Call the deployed backend API to retrieve live system data or diagnostics."
- **parameters**:
  - `method` (string, required): HTTP method (GET, POST, PUT, DELETE, etc.)
  - `path` (string, required): API path (e.g., `/items/`)
  - `body` (string, optional): JSON request body

### Authentication
- Uses `LMS_API_KEY` from environment to authenticate to the backend.
- Uses `AGENT_API_BASE_URL` from environment (default: `http://localhost:42002`).
- Uses header: `Authorization: Bearer <LMS_API_KEY>`.

### Response format
`query_api` returns a JSON string with:
- `status_code`: integer
- `body`: parsed JSON or raw text

## Environment Variables
The agent reads configuration from environment variables only:
- `LLM_API_KEY` (required)
- `LLM_API_BASE` (required)
- `LLM_MODEL` (required)
- `LMS_API_KEY` (required for `query_api` tool)
- `AGENT_API_BASE_URL` (optional, defaults to `http://localhost:42002`)

## System Prompt Strategy
- Clearly describe when to use each tool:
  - `read_file` / `list_files` for documentation and source code lookup
  - `query_api` for live system state / runtime data questions
- Instruct the model to only answer after gathering evidence from tools
- Request structured output with `answer`, optional `source`, and `tool_calls`

## Agentic Loop and Safeguards
- Keep existing agentic loop with tool calls in a single conversation
- Limit to 10 tool calls per question
- Handle null/empty message content safely
- Ensure stdout is valid JSON only; send diagnostics to stderr

## Benchmark Expectations (after first run)
- “What framework does the backend use?” → should read source files (FastAPI)
- “How many items are in the database?” → should call backend API via `query_api`
- Analytics errors → query API, inspect response, then read source to explain
- Docker / Docker Compose questions → read relevant config files
- ETL idempotency question → locate `external_id` checks in ETL code

## Failure Patterns and Iteration Plan
After the first benchmark run, analyze failures for common patterns:
- Missing tool calls (LLM didn’t use `query_api` when needed)
- Incorrect source parsing (source field missing or wrong)
- Tool errors due to path traversal or missing env vars

Iteration Plan:
1. Fix tool schemas or prompt to steer tool use
2. Improve `query_api` error handling and response formatting
3. Add targeted tests for failing benchmark questions
4. Validate `source` extraction logic and adjust prompt/generation
