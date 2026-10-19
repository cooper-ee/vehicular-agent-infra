"""Repeat CPU verification; never overwrites supplied evidence unless explicitly requested."""
import argparse
import ast
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('artifacts/verification'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    name = root.name
    pkg = {'vehicular-agent-infra': 'vai', 'roadside-multimodal-agent': 'rma', 'heterogeneous-inference-scheduler': 'his'}[name]
    env = {**os.environ, 'PYTHONUTF8': '1', 'BACKEND': 'mock', 'API_KEY': '', 'DATABASE': str(output / 'runtime.sqlite')}
    commands = [[sys.executable, '-m', 'pytest', '-ra']]
    if pkg == 'vai':
        commands += [[sys.executable, '-m', 'vai.cli', 'demo'], [sys.executable, '-m', 'vai.cli', 'benchmark', '--requests', '12', '--output', str(output / 'benchmark')]]
    if pkg == 'rma':
        commands += [[sys.executable, '-m', 'rma.cli', 'demo', '--output', str(output / 'demo')]]
        ast.parse((root / 'edge/jetson_client.py').read_text(encoding='utf-8'), feature_version=(3, 6))
    if pkg == 'his':
        commands += [[sys.executable, '-m', 'his.cli', 'evaluate', '--seeds', '1001', '1002', '--output', str(output / 'baselines')]]
    runs = []
    for index, command in enumerate(commands):
        result = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
        text = result.stdout + result.stderr
        text = text.replace(str(root), '<project>').replace(str(root.parents[2]), '<workspace>')
        for prefix in [str(Path(sys.base_prefix)), str(Path(sys.prefix)), os.getenv('TEMP', '')]:
            if prefix:
                text = text.replace(prefix, '<local-environment>')
        (output / ('check-%02d.log' % index)).write_text(text, encoding='utf-8')
        runs.append({'command': ['python'] + command[1:], 'exit_code': result.returncode, 'log': 'check-%02d.log' % index})
        if result.returncode:
            print(text)
            raise SystemExit(result.returncode)
    dependencies = ['fastapi', 'pydantic', 'httpx', 'pytest'] + {'vai': ['langgraph', 'numpy'], 'rma': ['Pillow'], 'his': ['numpy', 'gymnasium', 'stable-baselines3', 'torch']}[pkg]
    versions = {x: importlib.metadata.version(x) for x in dependencies}
    pytest_text = (output / 'check-00.log').read_text(encoding='utf-8')
    match = re.search(r'([0-9]+) passed', pytest_text)
    report = {'checked_date': '2026-10-19', 'project': name, 'status': 'passed',
              'tests_passed': int(match.group(1)) if match else None,
              'python': platform.python_version(), 'platform': platform.platform(), 'dependencies': versions,
              'commands': [{**r, 'command': [part.replace(str(output), '<output>') for part in r['command']]} for r in runs],
              'not_executed': ['GitHub Actions', 'Docker build', 'Jetson/Raspberry Pi device inference', 'vLLM/VLM neural inference'],
              'notes': 'CPU/offline and protocol verification only; see separate raw simulator and HTTP evidence'}
    (output / 'VERIFICATION.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'project': name, 'tests_passed': report['tests_passed'], 'status': report['status']}))


if __name__ == '__main__':
    main()
