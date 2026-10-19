# 设计与源码路线

本项目定位为 Agent 应用与服务集成。LangGraph 的 StateGraph/START/END 提供图执行；vLLM 在外部进程提供推理。
本仓库没有复制或重写上游状态引擎、PagedAttention 或连续批处理。

## 从一次请求读源码

1. `src/vai/api.py:create_app`：lifespan 创建服务；API Key 可选；Pydantic 校验输入。
2. `service.py:AgentService.run`：计数和整请求 deadline。
3. `_run`：request_id 锁 → 去重查询 → session 锁 → 读取对话 → 语料/历史绑定缓存 → 并发闸门。
4. `graph.py:build_graph`：模型响应存在 tool_calls 时转到工具节点，否则结束；轮数上限防止无限循环。
5. `backend.py:ChatBackend.complete`：真实 JSON 协议或可重复的 mock 调用。429/部分 5xx/网络错误有界重试，4xx 配置错误立即抛出。
6. `tools.py:ToolExecutor`：只支持明确登记的检索和时延估算工具，不执行任意 shell 或 Python。
7. `retrieval.py:Retriever`：固定顺序分块与向量排名；返回源文件名、字符偏移和得分。
8. `store.py:Store.save`：在同一 SQLite 事务中保存成功请求、对话与缓存。只保存完成后的对话问答，不保留中间工具消息。

## 具体建模

串行上传/等待/服务近似：

\[
T=1000\frac{8D_{\mathrm{MB}}}{B_{\mathrm{Mbps}}}+T_q+T_s.
\]

它是实验估算工具，不包含无线竞争、回传、信道误差和移动性。要做实际调度，应使用第三个项目并校准 profile。

默认检索使用 TF-IDF 加权向量的余弦相似度。中文按连续汉字段提取二元词，英文使用词法 token。
优点是无模型下载、可检查、低资源；同义词召回较弱。安装 `.[semantic]` 并配置 `EMBEDDING_MODEL` 后，改用该模型的归一化 embedding 余弦相似度。
当前只支持 .md；不应声称已经做 PDF/OCR 解析、向量数据库或复杂文档版面理解。

## 状态与故障边界

- 会话：按 session_id 串行；保存最近 20 条用户/助手消息；实际上下文仍受后端 token 上限约束。
- 幂等：相同 request_id 与 payload 返回已完成结果，不重复写入会话；相同 ID 改内容返回 409。
- 缓存：键包括模型、后端类型、语料 revision、历史和问题；TTL 默认 60 秒。首轮相同上下文可跨会话复用。
- 知识库在服务启动时构建索引，修改文件后需要重启。模型 ID 相同但权重变化时应清理旧缓存或更换数据库。
- 图运行中断后，客户端可以重试；没有持久化图节点 checkpoint，不能宣称 exactly-once、节点级恢复或可恢复工作流引擎。
- SQLite 操作为短同步事务，单机原型够用；高并发应迁移异步存储或服务化数据库，并实际压测。
- trace 的 model 节点计时包含重试；queue_ms 包含锁/存储/并发准入等前置等待，不能视作纯 vLLM 队列时延。

## 后续实验问题

对比词法与语义检索的 Recall@k；对比无缓存/有缓存；比较并发 1、2、4、8 下的错误率和 P95。
先固定模型、输入输出长度、后端版本，再讨论性能收益。推理后端自带的批处理能力归上游，应用层调优需要自己的对照记录。
