# API

启动：`vai serve`。可交互 schema：`http://127.0.0.1:8000/docs`。
设置 `API_KEY` 后，除 `/health` 外的业务接口要求 `Authorization: Bearer <key>`。默认仅监听回环地址。

| 方法 / 路径 | 用途 |
|---|---|
| GET /health | 当前后端与服务进程状态；不探测 GPU 模型可用性 |
| GET /metrics | 请求数、错误数、缓存命中、工具调用/失败累计数 |
| POST /v1/agent | 一次 Agent 对话 |
| POST /v1/agent/events | accepted → 完成后 trace → result/error 的 SSE 生命周期事件 |

```json
{"question":"车辆任务卸载如何考虑队列？","session_id":"car-01","request_id":"r-001","use_cache":true}
```

question 1..8000 字符，session_id/request_id 最长 100 字符。request_id 可省略，服务自动创建。
结果包含 answer、request_id、session_id、backend、cache_hit、replayed、exhausted、duration_ms、queue_ms、trace。
exhausted=true 表示工具循环达到上限，应按失败/未完成任务单独统计。

错误码：401 鉴权失败，409 请求 ID 冲突，422 输入校验失败，502 后端或协议错误，504 整请求超时。
SSE 建立后出现错误，通过 error 事件传达，而非修改已经发出的 HTTP 状态码。

示例：`python examples/client.py`。重复运行同一请求应返回 replayed=true。
保存的 SQLite 包含对话文本，部署者需自行设置实验数据保留策略。
