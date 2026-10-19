import json
import os
import httpx

headers = {'Authorization': 'Bearer ' + os.environ['API_KEY']} if os.getenv('API_KEY') else {}
with httpx.Client(timeout=50, headers=headers) as client:
    response = client.post('http://127.0.0.1:8000/v1/agent', json={
        'question': '比较节点任务数与归一化排队工作量的区别。',
        'session_id': 'learning-session', 'request_id': 'example-001'})
    response.raise_for_status()
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))
