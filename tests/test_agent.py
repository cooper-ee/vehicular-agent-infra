import asyncio
from dataclasses import replace
from fastapi.testclient import TestClient
import httpx
import pytest
from vai.api import create_app
from vai.backend import ChatBackend, assistant_message
from vai.config import Settings
from vai.service import AgentService, ConflictError


def settings(tmp_path, **kwargs):
    return Settings(database=str(tmp_path / 'test.sqlite'), **kwargs)


def test_graph_retrieval_and_idempotency(tmp_path):
    service = AgentService(settings(tmp_path))
    async def scenario():
        a, b = await asyncio.gather(service.run('车辆任务卸载', 's', 'id'), service.run('车辆任务卸载', 's', 'id'))
        assert a['answer'] == b['answer']
        assert sum(x['node'] == 'tool' for x in a['trace']) == 1
        assert len(service.store.history('s')) == 2
        assert not service.locks.items
        with pytest.raises(ConflictError):
            await service.run('different', 's', 'id')
    asyncio.run(scenario())


def test_estimate_and_invalid_tool(tmp_path):
    executor = AgentService(settings(tmp_path)).executor
    result = executor.execute('estimate_offload', dict(input_mb=1, bandwidth_mbps=80, queue_ms=10, service_ms=20, deadline_ms=150))
    assert result['estimated_ms'] == pytest.approx(130)
    assert result['deadline_met']
    assert not executor.execute('estimate_offload', {'bandwidth_mbps': 0})['ok']
    assert not executor.execute('shell', {})['ok']


def test_sessions_cache_and_restart(tmp_path):
    config = settings(tmp_path)
    service = AgentService(config)
    async def scenario():
        await service.run('排队时延', 's1', 'r1')
        second = await service.run('排队时延', 's2', 'r2')
        assert second['cache_hit']
        assert service.store.history('s1') == service.store.history('s2')
        assert (await AgentService(config).run('排队时延', 's1', 'r1'))['replayed']
    asyncio.run(scenario())


def test_timeout_and_tool_loop_limit(tmp_path):
    class Slow:
        async def complete(self, messages, tools):
            await asyncio.sleep(.1)
    service = AgentService(settings(tmp_path, timeout_s=.02), Slow())
    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(service.run('q'))
    class Loop:
        async def complete(self, messages, tools):
            return {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'x', 'type': 'function', 'function': {'name': 'bad', 'arguments': '{}'}}]}
    service = AgentService(settings(tmp_path, max_tool_rounds=2), Loop())
    result = asyncio.run(service.run('q'))
    assert result['exhausted']
    assert service.counters['tool_failures'] == 2


def test_api_auth_and_conflict(tmp_path):
    with TestClient(create_app(settings(tmp_path, api_key='test-only'))) as client:
        assert client.post('/v1/agent', json={'question': 'q'}).status_code == 401
        headers = {'Authorization': 'Bearer test-only'}
        assert client.post('/v1/agent', json={'question': 'q', 'request_id': 'x'}, headers=headers).status_code == 200
        assert client.post('/v1/agent', json={'question': 'changed', 'request_id': 'x'}, headers=headers).status_code == 409
        assert client.post('/v1/agent', json={'question': ''}, headers=headers).status_code == 422
        with client.stream('POST', '/v1/agent/events', json={'question': '时延'}, headers=headers) as response:
            assert 'event: result' in ''.join(response.iter_text())


def test_backend_retry_and_stream_protocol(tmp_path):
    attempts = []
    def handler(request):
        attempts.append(1)
        if request.url.path.endswith('/chat/completions') and len(attempts) == 1:
            return httpx.Response(503)
        import json
        payload = json.loads(request.content)
        if payload.get('stream'):
            return httpx.Response(200, text='data: {"choices":[{"delta":{"role":"assistant"}}]}\n\ndata: {"choices":[{"delta":{"content":"hello"}}]}\n\ndata: {"choices":[],"usage":{"completion_tokens":1}}\n\ndata: [DONE]\n\n')
        return httpx.Response(200, json={'choices': [{'message': {'role': 'assistant', 'content': 'ok'}}]})
    backend = ChatBackend(settings(tmp_path, backend='openai'), httpx.MockTransport(handler))
    async def scenario():
        assert (await backend.complete([{'role': 'user', 'content': 'q'}], []))['content'] == 'ok'
        assert len(attempts) == 2
        events = [event async for event in backend.stream('q')]
        assert ''.join(x['content'] for x in events) == 'hello'
        assert events[-1]['usage']['completion_tokens'] == 1
    asyncio.run(scenario())


def test_malformed_backend_responses_fail_explicitly():
    for value in [{}, {'choices': []}, {'choices': [{'message': {'content': 10}}]}]:
        with pytest.raises(ValueError):
            assistant_message(value)
