from typing import TypedDict
import time
from langgraph.graph import StateGraph, START, END


class AgentState(TypedDict):
    messages: list
    rounds: int
    trace: list
    exhausted: bool


def build_graph(backend, executor, max_rounds=3):
    async def model(state):
        start = time.perf_counter()
        message = await backend.complete(state['messages'], executor.schemas)
        calls = message.get('tool_calls') or []
        exhausted = bool(calls and state['rounds'] >= max_rounds)
        if exhausted:
            message = {'role': 'assistant', 'content': '工具调用已达到上限，请缩小问题或检查工具参数。'}
        return {'messages': state['messages'] + [message], 'exhausted': exhausted,
                'trace': state['trace'] + [{'node': 'model', 'duration_ms': (time.perf_counter() - start) * 1000}]}

    async def tools(state):
        messages, trace = list(state['messages']), list(state['trace'])
        calls = messages[-1].get('tool_calls', [])
        if len(calls) > 8:
            raise ValueError('At most 8 tool calls per round')
        for call in calls:
            start = time.perf_counter()
            message, result = executor.message(call)
            messages.append(message)
            trace.append({'node': 'tool', 'name': call['function']['name'], 'ok': result['ok'],
                          'duration_ms': (time.perf_counter() - start) * 1000})
        return {'messages': messages, 'rounds': state['rounds'] + 1, 'trace': trace}

    graph = StateGraph(AgentState)
    graph.add_node('model', model)
    graph.add_node('tools', tools)
    graph.add_edge(START, 'model')
    graph.add_conditional_edges('model', lambda state: 'tools' if state['messages'][-1].get('tool_calls') else END)
    graph.add_edge('tools', 'model')
    return graph.compile()
