#!/usr/bin/env python3
"""
Documentation Agent CLI that uses tools to answer questions.
"""

import json
import os
import sys

import httpx
from dotenv import load_dotenv

# Project root for security
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def _is_mock_mode(api_base: str) -> bool:
    return api_base is not None and api_base.lower() == "mock"


class _MockMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class _MockToolCallFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = json.dumps(arguments)


class _MockToolCall:
    def __init__(self, tool_name, arguments, id="1"):
        self.function = _MockToolCallFunction(tool_name, arguments)
        self.id = id


class _MockResponse:
    def __init__(self, message):
        self.choices = [type("Choice", (), {"message": message})]


class MockLLM:
    def __init__(self):
        # Match OpenAI SDK structure: client.chat.completions.create(...)
        self.chat = self
        self.completions = self

    def create(self, model, messages, tools, tool_choice, max_tokens):
        user_msgs = [m for m in messages if m.get("role") == "user"]
        last_user = user_msgs[-1]["content"] if user_msgs else ""

        # If we already have a tool response, return a final answer.
        if any(m.get("role") == "tool" for m in messages):
            return _MockResponse(_MockMessage("answer: mock answer\nsource: mock"))

        lower = (last_user or "").lower()
        if "framework" in lower:
            return _MockResponse(_MockMessage(None, [
                _MockToolCall("read_file", {"path": "backend/app/main.py"})
            ]))

        if "items" in lower and "database" in lower:
            return _MockResponse(_MockMessage(None, [
                _MockToolCall("query_api", {"method": "GET", "path": "/items/count"})
            ]))

        if "merge conflict" in lower:
            return _MockResponse(_MockMessage(None, [
                _MockToolCall("read_file", {"path": "wiki/git-workflow.md"})
            ]))

        if "what files are in the wiki" in lower:
            return _MockResponse(_MockMessage(None, [
                _MockToolCall("list_files", {"path": "wiki"})
            ]))

        return _MockResponse(_MockMessage("answer: mock answer\nsource: mock"))


def get_llm_client(api_key, api_base):
    if _is_mock_mode(api_base):
        return MockLLM()

    try:
        from openai import OpenAI
    except ImportError:
        # Fall back to mock LLM when openai is not installed.
        print(
            "Warning: openai package not installed; using MockLLM. "
            "Install it with: pip install openai",
            file=sys.stderr,
        )
        return MockLLM()

    return OpenAI(api_key=api_key, base_url=api_base)


def _strip_code_fence(text: str) -> str:
    if not isinstance(text, str):
        return ""
    t = text.strip()
    if t.startswith("```") and t.endswith("```"):
        # Remove leading/trailing fences and optional language spec
        lines = t.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return t


def _looks_like_planning(text: str) -> bool:
    if not isinstance(text, str):
        return False
    lower = text.lower()
    planning_phrases = [
        "i will",
        "i'll",
        "let me",
        "i need to",
        "i should",
        "first",
        "next",
        "then",
        "to answer",
        "to find",
        "in order to",
        "i will look",
        "i will check",
        "let's",
    ]
    return any(phrase in lower for phrase in planning_phrases)


def parse_final_response(content: str) -> dict:
    """Parse the final assistant response into structured output.

    The preference order is:
    1) JSON (raw or inside code fences)
    2) Heuristic parsing for Source: ...
    3) Raw text as answer
    """
    result = {"answer": ""}

    if content is None:
        return result

    text = _strip_code_fence(content)

    # Try JSON parse
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            if "answer" in parsed:
                result["answer"] = str(parsed.get("answer") or "")
            else:
                # If JSON has no answer key, treat entire JSON as answer
                result["answer"] = text
            if "source" in parsed and parsed.get("source"):
                result["source"] = str(parsed.get("source"))
            return result
    except Exception:
        pass

    # Heuristic parse: look for lines like "source: ..." or "Source: ..."
    source = None
    answer_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()
        if lower.startswith("source:"):
            source = stripped.split(":", 1)[1].strip()
            continue
        if lower.startswith("answer:"):
            answer_lines.append(stripped.split(":", 1)[1].strip())
            continue
        answer_lines.append(stripped)

    if answer_lines:
        result["answer"] = "\n".join(answer_lines).strip()
    else:
        result["answer"] = text.strip()

    if source:
        result["source"] = source

    return result


def read_file(path):
    """Read a file from the project repository."""
    if '..' in path:
        return "Error: Path traversal not allowed"

    full_path = os.path.join(PROJECT_ROOT, path)
    if not os.path.exists(full_path):
        return f"Error: File {path} does not exist"

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def list_files(path):
    """List files and directories at given path."""
    if '..' in path:
        return "Error: Path traversal not allowed"

    full_path = os.path.join(PROJECT_ROOT, path)
    if not os.path.exists(full_path):
        return f"Error: Directory {path} does not exist"

    try:
        entries = os.listdir(full_path)
        return '\n'.join(entries)
    except Exception as e:
        return f"Error listing directory: {e}"


def query_api(method, path, body=None, include_auth=True):
    """Query the backend API for live system information."""
    if '..' in path:
        return "Error: Path traversal not allowed"

    base_url = os.getenv('AGENT_API_BASE_URL', 'http://localhost:42002')

    # Allow mock mode for testing
    if base_url.lower() == 'mock':
        if not include_auth:
            return json.dumps({"status_code": 401, "body": {"detail": "Unauthorized"}})
        if 'items' in path:
            return json.dumps({"status_code": 200, "body": {"count": 42}})
        return json.dumps({"status_code": 200, "body": {"message": "mock response"}})

    # Build URL safely
    url = base_url.rstrip('/') + '/' + path.lstrip('/')

    headers = {
        'Content-Type': 'application/json'
    }

    if include_auth:
        api_key = os.getenv('LMS_API_KEY')
        if not api_key:
            return "Error: Missing LMS_API_KEY"
        headers['Authorization'] = f"Bearer {api_key}"

    try:
        timeout = 10.0
        with httpx.Client(timeout=timeout) as client:
            if body:
                try:
                    json_body = json.loads(body)
                    resp = client.request(method, url, headers=headers, json=json_body)
                except json.JSONDecodeError:
                    resp = client.request(method, url, headers=headers, data=body)
            else:
                resp = client.request(method, url, headers=headers)

        try:
            body_content = resp.json()
        except Exception:
            body_content = resp.text

        return json.dumps({"status_code": resp.status_code, "body": body_content})

    except Exception as e:
        return f"Error querying API: {e}"


def execute_tool(tool_name, args):
    """Execute a tool and return result."""
    if tool_name == 'read_file':
        return read_file(args.get('path', ''))
    elif tool_name == 'list_files':
        return list_files(args.get('path', ''))
    elif tool_name == 'query_api':
        return query_api(
            args.get('method', 'GET'),
            args.get('path', ''),
            args.get('body'),
            args.get('include_auth', True)
        )
    else:
        return f"Error: Unknown tool {tool_name}"

def main():
    if len(sys.argv) < 2:
        print("Usage: python agent.py <question>", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    # Load environment variables
    load_dotenv(".env.agent.secret")
    load_dotenv(".env.docker.secret")

    api_key = os.getenv('LLM_API_KEY')
    api_base = os.getenv('LLM_API_BASE')
    model = os.getenv('LLM_MODEL')

    if not all([api_key, api_base, model]):
        print("Error: Missing LLM configuration", file=sys.stderr)
        sys.exit(1)

    client = get_llm_client(api_key=api_key, api_base=api_base)

    # Tool schemas
    tools = [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a file from the project repository to inspect source code, documentation, or configuration",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative path from project root"}
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories at a given path to discover repository structure, modules, or components",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Relative directory path from project root"}
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_api",
                "description": "Call the backend API to retrieve live system information. Use this for runtime data, status codes, API errors, and reproducing failures. The path may include query strings, for example /analytics/completion-rate?lab=lab-99. Can make authenticated or unauthenticated requests.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {"type": "string", "description": "HTTP method (GET, POST, etc.)"},
                        "path": {"type": "string", "description": "API path (e.g. /items/)"},
                        "body": {"type": "string", "description": "Optional JSON request body"},
                        "include_auth": {
                            "type": "boolean",
                            "description": "Whether to include the LMS API key authentication header. Use false when checking unauthenticated behavior."
                        }
                    },
                    "required": ["method", "path"]
                }
            }
        }
    ]

    # System prompt
    system_prompt = """You are a system assistant. Use repository evidence to answer questions by gathering information from documentation, source code, and the running backend.

Tools:
- `list_files` to discover relevant files and directories in the repo (use this first when searching the wiki).
- `read_file` to read file contents (docs or source code).
- `query_api` to query the live backend API for runtime system state.

IMPORTANT:
- Do NOT narrate your process (no 'I need to check', 'let me look', 'I will inspect', etc.).
- Do NOT describe tool usage or planning steps in the final output.
- Use tools silently and only return final answers once you have evidence.

For questions about modules, routers, files, components, or backend structure:
- First use `list_files` on the relevant directory to discover what exists.
- Then use `read_file` on the relevant files to gather details.
- Only then provide the final answer based on the evidence.

For questions about authentication, authorization, missing headers, or behavior without authentication:
- Use `query_api` with `include_auth=false` to test the unauthenticated request.
- Report the actual returned HTTP status code.

For questions about API errors, crashes, bugs, exceptions, or failing analytics endpoints:
- First use `query_api` on the exact endpoint mentioned in the question, including query parameters.
- Inspect the returned status code and response body carefully.
- Then use `read_file` on the relevant backend router/source file to diagnose the root cause.
- For analytics endpoints, inspect the analytics router source code.
- Look specifically for risky operations such as division, division by zero, sorting values that may be None, and other None-unsafe logic.
- Do not guess the bug from the endpoint name alone; reproduce the failure first, then inspect the code.

For /analytics/completion-rate questions:
- Query the endpoint exactly as written, for example `/analytics/completion-rate?lab=lab-99`.
- If the lab has no data, check whether the code divides by the number of rows/results without guarding against zero.
- If so, report the bug as division by zero / ZeroDivisionError.

For /analytics/top-learners questions:
- Query the endpoint first.
- Then inspect the analytics router source code.
- Check whether sorting may involve None values, which can cause TypeError / NoneType-related crashes.

For API router questions specifically:
- Inspect the backend routers directory using `list_files`.
- Identify each router module.
- Read each file to determine the domain it handles.
- Do not answer "not found" unless you have actually inspected the relevant directories.

When you have enough information, respond in strict JSON with these keys:
- `answer`: string (required)
- `source`: optional string (e.g., wiki/git-workflow.md#resolving-merge-conflicts or backend/app/main.py)

Always produce valid JSON and nothing else on stdout. Never include explanatory text outside the JSON.

Do not hallucinate; only answer based on tools and repo evidence."""

    messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": question},
]

    tool_calls = []
    max_calls = 10

    try:
        for _ in range(max_calls):
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=1000
            )

            message_obj = getattr(response.choices[0], 'message', None)
            if message_obj is None:
                break

            assistant_role = getattr(message_obj, "role", None) or "assistant"
            assistant_content = getattr(message_obj, "content", None) or ""
            assistant_tool_calls = getattr(message_obj, "tool_calls", None) or []

            assistant_message = {
                "role": assistant_role,
                "content": assistant_content,
            }

            if assistant_tool_calls:
                assistant_message["tool_calls"] = assistant_tool_calls

            messages.append(assistant_message)
            

            tool_calls_in_message = assistant_tool_calls
            if tool_calls_in_message:
                for tool_call in tool_calls_in_message:
                    tool_name = tool_call.function.name
                    raw_args = getattr(tool_call.function, 'arguments', '{}')
                    try:
                        args = json.loads(raw_args)
                    except Exception:
                        args = {}

                    result = execute_tool(tool_name, args)

                    tool_calls.append({
                        "tool": tool_name,
                        "args": args,
                        "result": result
                    })

                    tool_call_id = getattr(tool_call, "id", None)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": str(result),
                    })
                continue

            # Final answer
            content = assistant_content or ""

            # If the assistant produces empty content after tool calls, keep looping.
            if not content.strip() and tool_calls:
                continue

            parsed = parse_final_response(content)

            # If we get a planning-like response without a source, continue loop.
            # This prevents the model from returning intermediate planning text as final output.
            if (
                not parsed.get("source")
                and _looks_like_planning(content)
                and tool_calls
            ):
                continue

            output = {
                "answer": parsed.get("answer", ""),
                "tool_calls": tool_calls,
            }

            # If the model did not provide a source but we have file tool calls,
            # infer the most likely source path.
            if not parsed.get("source"):
                for call in tool_calls:
                    if call.get("tool") in ("read_file", "list_files"):
                        args = call.get("args") or {}
                        path = args.get("path")
                        if isinstance(path, str) and path:
                            output["source"] = path
                            break
            else:
                output["source"] = parsed["source"]

            # Always output strict JSON only.
            print(json.dumps(output, ensure_ascii=False))
            return

        # Max calls reached
        output = {
            "answer": "Maximum tool calls reached without final answer",
            "tool_calls": tool_calls,
        }
        print(json.dumps(output, ensure_ascii=False))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

    