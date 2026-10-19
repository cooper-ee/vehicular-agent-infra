import argparse
import asyncio
import csv
import json
import platform
import subprocess
import time
import uuid
from dataclasses import replace
from pathlib import Path
from .backend import ChatBackend
from .config import Settings
from .service import AgentService


async def benchmark(settings, count, concurrency, output, mode, prompt):
    if count < 1 or concurrency < 1:
        raise ValueError('count and concurrency must be positive')
    output.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(concurrency)
    service = AgentService(settings) if mode == 'agent' else None
    backend = ChatBackend(settings)
    rows = []
    gpu_rows = []
    monitor_stop = asyncio.Event()

    def read_gpu():
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=index,memory.used,utilization.gpu', '--format=csv,noheader,nounits'],
                                    capture_output=True, text=True, timeout=2, check=True)
            return [dict(zip(['gpu_index', 'memory_used_mb', 'utilization_percent'], [float(x.strip()) for x in line.split(',')])) for line in result.stdout.splitlines()]
        except (OSError, ValueError, subprocess.SubprocessError):
            return []

    async def monitor():
        while not monitor_stop.is_set():
            for row in await asyncio.to_thread(read_gpu):
                gpu_rows.append({'timestamp': time.time(), **row})
            try:
                await asyncio.wait_for(monitor_stop.wait(), .25)
            except asyncio.TimeoutError:
                pass

    async def request(index):
        async with semaphore:
            start = time.perf_counter()
            first = None
            row = {'index': index, 'mode': mode, 'backend': settings.backend, 'success': False,
                   'duration_ms': None, 'ttft_ms': None, 'completion_tokens': None,
                   'tool_calls': 0, 'tool_failures': 0, 'error': ''}
            try:
                if service:
                    result = await service.run(prompt, session_id=str(uuid.uuid4()), use_cache=False)
                    row['tool_calls'] = sum(x['node'] == 'tool' for x in result['trace'])
                    row['tool_failures'] = sum(x['node'] == 'tool' and not x['ok'] for x in result['trace'])
                    row['success'] = not result['exhausted'] and bool(result['answer'])
                else:
                    async def consume():
                        nonlocal first
                        async for event in backend.stream(prompt):
                            if event['content'] and first is None:
                                first = time.perf_counter()
                            if event['usage']:
                                row['completion_tokens'] = event['usage'].get('completion_tokens')
                    await asyncio.wait_for(consume(), settings.timeout_s)
                    row['ttft_ms'] = (first - start) * 1000 if first is not None else None
                    row['success'] = first is not None
            except Exception as error:
                row['error'] = type(error).__name__
            row['duration_ms'] = (time.perf_counter() - start) * 1000
            return row

    monitor_task = asyncio.create_task(monitor())
    started = time.perf_counter()
    rows = await asyncio.gather(*(request(i) for i in range(count)))
    elapsed = time.perf_counter() - started
    monitor_stop.set()
    await monitor_task
    good = [r for r in rows if r['success']]
    def percentile(values, p):
        if not values:
            return None
        ordered = sorted(values)
        index = (len(ordered) - 1) * p
        lower = int(index)
        return ordered[lower] + (ordered[min(lower + 1, len(ordered) - 1)] - ordered[lower]) * (index - lower)
    tokens = [r['completion_tokens'] for r in good]
    summary = {'backend': settings.backend, 'model': settings.model, 'mode': mode, 'requests': count,
               'concurrency': concurrency, 'prompt_characters': len(prompt), 'prompt': prompt,
               'success_rate': len(good) / count, 'wall_s': elapsed, 'successful_requests_per_s': len(good) / elapsed,
               'latency_p50_ms': percentile([r['duration_ms'] for r in good], .5),
               'latency_p95_ms': percentile([r['duration_ms'] for r in good], .95),
               'ttft_p95_ms': percentile([r['ttft_ms'] for r in good if r['ttft_ms'] is not None], .95),
               'completion_tokens_per_s': sum(tokens) / elapsed if tokens and all(t is not None for t in tokens) else None,
               'tool_success_rate': 1 - sum(r['tool_failures'] for r in rows) / sum(r['tool_calls'] for r in rows) if sum(r['tool_calls'] for r in rows) else None,
               'python': platform.python_version(), 'platform': platform.platform(),
               'gpu_total_memory_peak_mb_sampled': max((r['memory_used_mb'] for r in gpu_rows), default=None),
               'gpu_sample_scope': 'total device memory; includes unrelated processes; sampled peak can miss brief spikes',
               'interpretation': 'mock results measure protocol overhead only; not LLM throughput' if settings.backend == 'mock' else 'client-observed latency; token throughput only when usage is available'}
    with (output / 'requests.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    if gpu_rows:
        with (output / 'gpu.csv').open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(gpu_rows[0]))
            writer.writeheader()
            writer.writerows(gpu_rows)
    return summary


def main():
    parser = argparse.ArgumentParser(description='Vehicular Agent Infra')
    sub = parser.add_subparsers(dest='command', required=True)
    demo = sub.add_parser('demo')
    demo.add_argument('--question', default='车辆任务卸载如何兼顾排队时延和负载均衡？')
    bench = sub.add_parser('benchmark')
    bench.add_argument('--requests', type=int, default=20)
    bench.add_argument('--concurrency', type=int, default=4)
    bench.add_argument('--mode', choices=['agent', 'model-stream'], default='agent')
    bench.add_argument('--prompt', default='解释车辆任务卸载中的队列时延和负载均衡。')
    bench.add_argument('--output', type=Path, default=Path('artifacts/benchmark'))
    sub.add_parser('serve')
    args = parser.parse_args()
    settings = Settings.from_env()
    if args.command == 'demo':
        service = AgentService(settings)
        result = asyncio.run(service.run(args.question, session_id='demo-' + str(uuid.uuid4())))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == 'benchmark':
        print(json.dumps(asyncio.run(benchmark(settings, args.requests, args.concurrency, args.output, args.mode, args.prompt)), ensure_ascii=False, indent=2))
    else:
        import uvicorn
        uvicorn.run('vai.api:create_app', factory=True, host='127.0.0.1', port=8000)


if __name__ == '__main__':
    main()
