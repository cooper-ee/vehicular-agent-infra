# 部署

## 本地与 Docker

Python 3.10+。`python -m pip install -e ".[dev]"`；需要约束本次测试依赖时使用 `python -m pip install -c requirements.lock.txt -e ".[dev]"`。
`requirements.lock.txt` 为本次 Windows 测试环境的依赖约束，跨系统差异见文件头；不是模型服务镜像锁。
`docker compose up --build` 启动 CPU/mock 服务。Docker 配置随包提供，本次未执行 Docker 构建。
真实部署保持一个 Uvicorn worker，否则进程内会话锁与并发控制无法跨进程协调。

## vLLM 独立推理服务

官方安装入口：[vLLM GPU 安装](https://docs.vllm.ai/en/stable/getting_started/installation/gpu/)。
vLLM 的主要 GPU 运行环境是 Linux；Windows 主机先准备兼容的 WSL2/Linux GPU 环境，不能直接把当前 Windows Python 环境当作已可运行的 vLLM 环境。
RTX 50 系列需同时核对驱动、CUDA、PyTorch 和 vLLM 对硬件的支持，保留 `nvidia-smi`、`python -m pip freeze`、模型 revision 和启动日志。

1. 在新的 Linux 环境按官方方式安装与 GPU 兼容的 vLLM；不要改动已有科研 conda 环境。
2. 执行 `bash deploy/serve_vllm.sh`。默认候选 `Qwen/Qwen3-1.7B`，约束 4096 context、2 sequences、eager 模式；这些是待实测的起始参数，不保证所有驱动/版本都能装入 8GB。
3. 查看 `http://127.0.0.1:8001/v1/models`，确认 local-model 已注册。OpenAI 兼容服务的 tools 解析需开启相应 parser，见 [工具调用](https://docs.vllm.ai/en/stable/features/tool_calling/)。
4. 在应用进程设置 BACKEND、LLM_BASE_URL、LLM_MODEL。跨 WSL/容器连接时按实际网络修改地址；容器里的 127.0.0.1 指向容器自身。
5. 先做单请求工具 smoke test，再做并发压测。上下文过长先减小历史/知识片段或提高可用 context；OOM 先降并发和 context。

`.env.example` 不会自动加载；PowerShell 使用 `$env:BACKEND='openai'`，bash 使用 `export BACKEND=openai`。
后端 API Key 通过 LLM_API_KEY；应用 API Key 通过 API_KEY，两者用途不同。

## 可选语义检索

安装 `python -m pip install -e ".[semantic]"`，将 EMBEDDING_MODEL 设置为自己选择的 SentenceTransformer 模型目录。
首次使用远程模型 ID 可能下载权重；模型不随 ZIP 分发，本次未下载或运行语义 embedding。
评估时明确区分 TF-IDF 向量与神经语义向量，不能把二者都写成已经训练的领域 embedding。
