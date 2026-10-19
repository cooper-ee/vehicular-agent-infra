import asyncio
import json
import httpx


def assistant_message(data):
    try:
        message = data['choices'][0]['message']
        calls = message.get('tool_calls') or []
        if not isinstance(message.get('content'), (str, type(None))) or not isinstance(calls, list):
            raise ValueError('invalid assistant message')
        for call in calls:
            if not all(isinstance(x, str) and x for x in [call['id'], call['function']['name'], call['function']['arguments']]):
                raise ValueError('invalid tool call')
        if not calls and not message.get('content'):
            raise ValueError('empty assistant message')
        result = {'role': 'assistant', 'content': message.get('content')}
        if calls:
            result['tool_calls'] = calls
        return result
    except (IndexError, KeyError, TypeError, AttributeError) as error:
        raise ValueError('invalid chat completion protocol') from error


class ChatBackend:
    def __init__(self, settings, transport=None):
        self.settings = settings
        self.transport = transport

    def client(self):
        headers = {'Authorization': 'Bearer ' + self.settings.backend_key} if self.settings.backend_key else {}
        return httpx.AsyncClient(base_url=self.settings.base_url + '/', headers=headers,
                                 timeout=self.settings.timeout_s, transport=self.transport)

    async def complete(self, messages, tools):
        if self.settings.backend == 'mock':
            # A deterministic protocol fixture; no neural-model inference is performed.
            if messages[-1]['role'] == 'tool':
                return {'role': 'assistant', 'content': '[MOCK/协议演示] 工具执行结果：' + messages[-1]['content']}
            question = messages[-1]['content']
            return {'role': 'assistant', 'content': None, 'tool_calls': [
                {'id': 'lookup-1', 'type': 'function', 'function': {'name': 'search_knowledge', 'arguments': json.dumps({'query': question}, ensure_ascii=False)}}]}
        payload = {'model': self.settings.model, 'messages': messages, 'temperature': 0,
                   'max_tokens': 512, 'tools': tools, 'tool_choice': 'auto'}
        async with self.client() as client:
            for attempt in range(3):
                try:
                    response = await client.post('chat/completions', json=payload)
                    response.raise_for_status()
                    return assistant_message(response.json())
                except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as error:
                    if isinstance(error, httpx.HTTPStatusError) and error.response.status_code not in {429, 500, 502, 503, 504}:
                        raise
                    if attempt == 2:
                        raise
                    await asyncio.sleep(0.1 * 2 ** attempt)

    async def stream(self, prompt):
        if self.settings.backend == 'mock':
            for part in ['[MOCK] ', '车载边缘', '推理协议', '测试。']:
                yield {'content': part, 'usage': None}
            yield {'content': '', 'usage': {'completion_tokens': None, 'mock': True}}
            return
        payload = {'model': self.settings.model, 'messages': [{'role': 'user', 'content': prompt}],
                   'temperature': 0, 'max_tokens': 128, 'stream': True,
                   'stream_options': {'include_usage': True}}
        async with self.client() as client:
            async with client.stream('POST', 'chat/completions', json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith('data:'):
                        continue
                    data = line[5:].strip()
                    if data == '[DONE]':
                        break
                    event = json.loads(data)
                    choices = event.get('choices') or []
                    content = (choices[0].get('delta', {}).get('content') or '') if choices else ''
                    yield {'content': content, 'usage': event.get('usage')}
