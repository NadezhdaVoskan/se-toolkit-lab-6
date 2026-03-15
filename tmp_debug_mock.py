from agent import MockLLM

llm = MockLLM()
msgs = [{'role': 'user', 'content': 'How do you resolve a merge conflict?', 'tool_calls': []}]
for i in range(5):
    resp = llm.create(model='m', messages=msgs, tools=None, tool_choice=None, max_tokens=10)
    msg = resp.choices[0].message
    print('iter', i, 'content=', repr(msg.content), 'tool_calls=', getattr(msg, 'tool_calls', None))
    # simulate agent appending the message as a dict like in agent.py
    msgs.append({'role': getattr(msg, 'role', None) or 'assistant', 'content': msg.content, 'tool_calls': getattr(msg, 'tool_calls', [])})
