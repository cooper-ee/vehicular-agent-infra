# 上游来源与开发说明

本仓库代码为围绕车载边缘计算场景编写的应用层实现，使用或参考下列开源项目的公开接口与文档。
没有将上游整个仓库改名打包，没有复制上游核心引擎，没有修改或重新实现其底层优化算法。
依赖的许可证由各自作者保留；本仓库 MIT 许可证仅覆盖本仓库新增代码。
作者署名 Yi Qin 对应个人项目维护归属；代码由 Codex 辅助生成、调试和验证，不能据此声称逐行手工编写。

| 上游 | 上游许可证（查询时） | 核对提交 |
|---|---|---|
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | MIT | `98043c37abc60374030f960a03a6e0d4c0112643` |
| [vllm-project/vllm](https://github.com/vllm-project/vllm) | Apache-2.0 | `fc47cc8fff8282b7fa2b257468b8595f91a1a741` |
| [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | MIT | `4fe944a581895ab47b0f56e204829594d5ba74a8` |
| [infiniflow/ragflow](https://github.com/infiniflow/ragflow) | Apache-2.0 | `b811e5bf67342b15d17030537dc893296519ade0` |

具体核对文件、永久链接和 SHA-256 见 docs/upstream-snapshot.json。记录 unavailable 的文件没有成功取得，不作为已读证据。
核对时间为 2026-10-19；提交快照用于说明参考来源，安装依赖版本由 pyproject.toml 和 requirements.lock.txt 决定。
模型权重、数据集及其独立许可不包含在仓库中，使用时需查看对应模型/数据卡。
RAGFlow、LangChain、ncnn 或 RK3576 路线仅在说明中出现时，均不代表已集成这些项目。
