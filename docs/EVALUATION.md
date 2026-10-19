# 推理评估与指标解释

| 模式 | 测量内容 | 不能据此声称 |
|---|---|---|
| mock + agent | 本地编排、工具、SQLite 路径与错误率 | GPU LLM 性能 |
| openai + agent | 多次模型/工具调用的端到端耗时、协议完成率 | 单次模型 TTFT |
| openai + model-stream | 直连模型客户端 TTFT、端到端延迟与后端 usage token | 复杂 Agent 语义任务正确率 |

`requests.csv` 保留成功和失败请求；摘要 P50/P95 只对成功请求计算，必须同时看 success_rate。
success_rate 是协议完成率，不是人工语义准确率；exhausted 不算完成。tool_success_rate 是参数/执行状态成功率，不代表工具决策正确。
TTFT 从发起请求到首个非空文本增量，流事件不是 token 数；输出 token/s 仅在所有成功请求返回 completion_tokens 时计算，否则 null。
GPU 显存用 nvidia-smi 周期采样设备总量，含桌面和其他进程；不能直接当作 vLLM 独占显存或精确瞬时峰值。

建议矩阵：并发 {1,2,4,8} × 中文输入长度 {100,500,1500}；固定输出上限、模型、温度与 context。
每组先 warmup，正式至少 200 请求并重复 3 次；长时间压测另检查错误增长、SQLite 写入与缓存大小。
本次 evidence 的少量请求用于可运行性验证，样本不足以支持高性能结论。

```powershell
vai benchmark --mode agent --requests 200 --concurrency 1 --output artifacts/agent-c1
vai benchmark --mode agent --requests 200 --concurrency 4 --output artifacts/agent-c4
vai benchmark --mode model-stream --requests 200 --concurrency 2 --output artifacts/model-c2
```

缓存压测应单独编写带固定上下文/不同 ID 的请求集合；CLI 默认关闭缓存且每次使用新会话，避免重复问答把缓存吞吐误写为推理吞吐。
真实 RAG 质量需建立有标注的问题—文档对，并记录 Recall@k、来源正确率和最终答案质量；仓库暂不附未标注的“准确率”。
