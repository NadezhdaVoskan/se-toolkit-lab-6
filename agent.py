#!/usr/bin/env python3
"""
Documentation Agent CLI that uses tools to answer questions.
"""

import json
import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

# Project root for security
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

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

def execute_tool(tool_name, args):
    """Execute a tool and return result."""
    if tool_name == 'read_file':
        return read_file(args.get('path', ''))
    elif tool_name == 'list_files':
        return list_files(args.get('path', ''))
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

    client = OpenAI(api_key=api_key, base_url=api_base)

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
        }
    ]

    # System prompt
    system_prompt = """You are a documentation assistant. Use the available tools to find information in the wiki/ directory to answer questions accurately.

When you have enough information, provide a final answer with:
- answer: Your response
- source: Wiki section reference (e.g., wiki/git-workflow.md#resolving-merge-conflicts)

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

            message = response.choices[0].message
            messages.append(message)

            if message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    result = execute_tool(tool_name, args)
                    
                    tool_calls.append({
                        "tool": tool_name,
                        "args": args,
                        "result": result
                    })
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })
            else:
                # Final answer
                content = message.content
                # Parse answer and source from content
                answer = content
                source = ""
                if "answer:" in content.lower():
                    # Try to extract structured response
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

    