#!/usr/bin/env bash
set -euo pipefail
# Execute inside a separately prepared Linux/WSL2 vLLM environment.
# Candidate configuration for 8GB VRAM, not a measured compatibility guarantee.
vllm serve "${MODEL_ID:-Qwen/Qwen3-1.7B}"   --served-model-name local-model --host 127.0.0.1 --port 8001   --dtype auto --max-model-len 4096 --max-num-seqs 2   --gpu-memory-utilization 0.75 --enforce-eager   --enable-auto-tool-choice --tool-call-parser hermes   --chat-template-kwargs '{"enable_thinking":false}'
