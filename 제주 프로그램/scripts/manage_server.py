"""Interactive launcher; owns and stops only the processes it starts."""
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'runtime'
PROCESSES = []
LOGS = []


def start(name, args, env=None):
    log = (RUNTIME / f'server-{name}.log').open('w', encoding='utf-8')
    LOGS.append(log)
    process = subprocess.Popen(args, cwd=ROOT, env=env, stdout=log, stderr=log,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    PROCESSES.append(process)
    return process


def stop():
    for process in reversed(PROCESSES):
        if process.poll() is None:
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NO_WINDOW)
            process.wait(timeout=10)
    PROCESSES.clear()
    for log in LOGS:
        log.close()
    LOGS.clear()


def wait_ready(url, process):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(120):
        if process.poll() is not None:
            raise RuntimeError('서버가 종료되었습니다. runtime/server-*.log를 확인하세요.')
        try:
            with opener.open(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (OSError, ValueError):
            pass
        time.sleep(.5)
    raise RuntimeError('서버 준비 시간이 초과되었습니다. 실행 기록을 확인하세요.')


def launch(public=False):
    if PROCESSES:
        raise RuntimeError('먼저 3번으로 기존 서버를 종료하세요.')
    for port in (8766, 8770):
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1', port)) == 0:
                raise RuntimeError(f'{port} 포트를 사용 중입니다. 기존 서버를 먼저 종료하세요.')
    for relative in ('dist/llama-server.exe', 'dist/models/qwen2.5-1.5b-instruct-q4_k_m.gguf',
                     'frontend/dist/index.html', 'runtime/demo-seed.db', 'runtime/public-data.db'):
        if not (ROOT / relative).is_file():
            raise RuntimeError(f'필수 파일이 없습니다: {relative}')
    RUNTIME.mkdir(exist_ok=True)
    print('AI 서버를 준비하고 있습니다…', flush=True)
    model = start('model', [str(ROOT / 'dist/llama-server.exe'), '-m',
        str(ROOT / 'dist/models/qwen2.5-1.5b-instruct-q4_k_m.gguf'), '--host', '127.0.0.1',
        '--port', '8766', '--ctx-size', '4096', '--parallel', '1', '--no-webui', '--log-disable'])
    wait_ready('http://127.0.0.1:8766/health', model)
    origin = 'http://127.0.0.1:8770'
    if public:
        tunnel = start('tunnel', [r'C:\Program Files (x86)\cloudflared\cloudflared.exe',
            'tunnel', '--url', origin, '--no-autoupdate'])
        for _ in range(120):
            if tunnel.poll() is not None:
                raise RuntimeError('외부 연결이 종료되었습니다. server-tunnel.log를 확인하세요.')
            found = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com',
                             (RUNTIME / 'server-tunnel.log').read_text(encoding='utf-8', errors='replace'))
            if found:
                origin = found.group(0)
                break
            time.sleep(.5)
        else:
            raise RuntimeError('임시 주소 발급 시간이 초과되었습니다.')
    env = dict(os.environ, DEMO_PUBLIC_ORIGIN=origin, APP_PORT='8770',
               LLM_URL='http://127.0.0.1:8766')
    web = start('web', [sys.executable, '-m', 'uvicorn', 'backend.app.main:app',
                       '--host', '127.0.0.1', '--port', '8770', '--no-access-log'], env)
    wait_ready('http://127.0.0.1:8770/', web)
    (RUNTIME / 'server-address.txt').write_text(origin + '\n', encoding='utf-8')
    print(f'서버 실행 완료! 접속 주소: {origin}\n이 창을 유지하세요. 브라우저는 직접 열어 주세요.')


def main():
    try:
        while True:
            print('\n=== 제주 결산 서버 관리 ===\n1. 내 PC에서 실행 (웹 + AI)'
                  '\n2. 외부 공유용 실행 (웹 + AI + 임시 주소)\n3. 서버 종료\n0. 서버 종료 후 창 닫기')
            print('자동 데이터 수집은 이 창과 별개로 유지됩니다.')
            choice = input('번호 선택: ').strip()
            if choice == '0':
                break
            try:
                if choice in ('1', '2'):
                    launch(public=choice == '2')
                elif choice == '3':
                    stop()
                    print('이 관리 창에서 실행한 서버를 종료했습니다.')
                else:
                    print('0~3 사이 번호를 선택하세요.')
            except Exception as error:
                if choice in ('1', '2'):
                    stop()
                print(f'오류: {error}')
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        stop()


if __name__ == '__main__':
    main()
