#!/usr/bin/env python3
"""
Agent CLI that calls an LLM and returns JSON response.
"""

import json
import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

def main():
    if len(sys.argv) < 2:
        print("Usage: python agent.py <question>", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    # Load environment variables from .env.agent.secret
    load_dotenv('.env.agent.secret')

    api_key = os.getenv('LLM_API_KEY')
    api_base = os.getenv('LLM_API_BASE')
    model = os.getenv('LLM_MODEL')

    if not all([api_key, api_base, model]):
        print("Error: Missing LLM configuration in environment variables", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(
        api_key=api_key,
        base_url=api_base,
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": question}],
            max_tokens=1000,
        )
        answer = response.choices[0].message.content
        tool_calls = []  # No tools implemented yet

        output = {
            "answer": answer,
            "tool_calls": tool_calls
        }
        print(json.dumps(output))
    except Exception as e:
        print(f"Error calling LLM: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

    