#!/usr/bin/env python3
"""
Documentation Agent CLI that uses tools to answer questions.
"""

import json
import os
import sys

import httpx
from dotenv import load_dotenv
from openai import OpenAI

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
    def chat(self):
        return self

    def completions(self):
        return self

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
    return OpenAI(api_key=api_key, base_url=api_base)


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


def query_api(method, path, body=None):
    """Query the backend API for live system information."""
    if '..' in path:
        return "Error: Path traversal not allowed"

    base_url = os.getenv('AGENT_API_BASE_URL', 'http://localhost:42002')
    # Allow mock mode for testing
    if base_url.lower() == 'mock':
        # Return a stable mock response based on path
        if 'items' in path:
            return json.dumps({"status_code": 200, "body": {"count": 42}})
        return json.dumps({"status_code": 200, "body": {"message": "mock response"}})

    api_key = os.getenv('LMS_API_KEY')
    if not api_key:
        return "Error: Missing LMS_API_KEY"

    # Build URL safely
    url = base_url.rstrip('/') + '/' + path.lstrip('/')

    headers = {
        'Authorization': f"Bearer {api_key}",
        'Content-Type': 'application/json'
    }

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
            args.get('body')
        )
    else:
        return f"Error: Unknown tool {tool_name}"

def main():
    if len(sys.argv) < 2:
        print("Usage: python agent.py <question>", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    # Load environment variables
    load_dotenv('.env.agent.secret')

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
                "description": "Read a file from the project repository",
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
                "description": "List files and directories at given path",
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
                "description": "Call the backend API to retrieve live system information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {"type": "string", "description": "HTTP method (GET, POST, etc.)"},
                        "path": {"type": "string", "description": "API path (e.g. /items/)"},
                        "body": {"type": "string", "description": "JSON request body", "nullable": True}
                    },
                    "required": ["method", "path"]
                }
            }
        }
    ]

    # System prompt
    system_prompt = """You are a system assistant. Use the available tools to answer questions by gathering evidence from documentation, source code, and the running backend.

Tools:
- `read_file` / `list_files` for documentation and source code lookup.
- `query_api` for live system state and runtime data.

When you have enough information, provide a final answer with:
- answer: Your response
- source: Optional reference (e.g., wiki/git-workflow.md#resolving-merge-conflicts)

Do not make up information. Use tools to verify facts."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
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

            message = getattr(response.choices[0], 'message', None)
            if message is None:
                break

            messages.append(message)

            tool_calls_in_message = getattr(message, 'tool_calls', []) or []
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

                    messages.append({
                        "role": "tool",
                        "tool_call_id": getattr(tool_call, 'id', None),
                        "content": result
                    })
                continue

            # Final answer
            content = getattr(message, 'content', '') or ''

            answer = content
            source = ""
            if isinstance(content, str) and "answer:" in content.lower():
                lines = content.split('\n')
                for line in lines:
                    if line.lower().startswith("answer:"):
                        answer = line.split(":", 1)[1].strip()
                    elif line.lower().startswith("source:"):
                        source = line.split(":", 1)[1].strip()

            output = {
                "answer": answer,
                "source": source,
                "tool_calls": tool_calls
            }
            print(json.dumps(output))
            return

        # Max calls reached
        output = {
            "answer": "Maximum tool calls reached without final answer",
            "source": "",
            "tool_calls": tool_calls
        }
        print(json.dumps(output))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

    