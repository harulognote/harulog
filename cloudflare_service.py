"""Private origin + authenticated Cloudflare access. No shared process termination."""
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import threading
import time
from urllib.parse import urlsplit
import urllib.request
import urllib.error



def find_cloudflared(root):
    configured = os.getenv('CLOUDFLARED_PATH', '').strip()
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
        if candidate.is_file():
            return str(candidate.resolve())
        raise RuntimeError('CLOUDFLARED_PATH 파일을 찾을 수 없습니다.')
    for folder in (root / 'TOOLS', root.parent / 'TOOLS', root):
        for name in ('cloudflared.exe', 'cloudflared-windows-amd64.exe', 'cloudflared'):
            candidate = folder / name
            if candidate.is_file():
                return str(candidate.resolve())
    found = shutil.which('cloudflared')
    if found:
        return found
    raise RuntimeError('cloudflared가 없습니다. 기존 TOOLS 폴더의 실행파일을 사용하거나 .env에 CLOUDFLARED_PATH를 설정해 주세요.')


def public_url(value):
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RuntimeError('HARULOG_PUBLIC_URL에 고정 Tunnel의 HTTPS 주소를 입력해 주세요.')
    if parsed.path not in ('', '/'):
        raise RuntimeError('고정 Tunnel은 하위 경로 대신 전용 호스트명을 사용해 주세요.')
    return value.rstrip('/')


def tunnel_command(executable, root, port):
    # An isolated empty config avoids conflicts with another application's default config.yml.
    config = root / 'runtime' / 'quick-tunnel.yml'
    config.parent.mkdir(exist_ok=True)
    config.write_text('{}\n', encoding='utf-8')
    return [executable, 'tunnel', '--config', str(config), '--no-autoupdate',
            '--url', f'http://127.0.0.1:{port}']


def stop_process(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def wait_for_url(process, timeout=60, log=None):
    lines = queue.Queue()
    def read():
        try:
            for line in process.stdout:
                if log is not None:
                    log.write(line)
                    log.flush()
                lines.put(line)
        finally:
            lines.put(None)
    process._harulog_reader = threading.Thread(target=read, daemon=True)
    process._harulog_reader.start()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError('Cloudflare가 종료되었습니다. runtime/cloudflared.log를 확인해 주세요.')
        try:
            line = lines.get(timeout=min(0.5, max(0.01, deadline-time.monotonic())))
        except queue.Empty:
            continue
        if line is None:
            raise RuntimeError('Cloudflare 출력이 종료되었습니다.')
        match = re.search(r'https://[a-z0-9]+(?:-[a-z0-9]+)*\.trycloudflare\.com\b', line)
        if match:
            # Keep draining stdout so the child never blocks on its pipe.
            return match.group(0), lines
    raise RuntimeError('60초 내 외부 주소를 받지 못했습니다. 외부 통신/Cloudflare 상태와 로그를 확인해 주세요.')


def run(app, root, port, existing=False):
    executable = None if existing else find_cloudflared(root)
    url = public_url(os.getenv('HARULOG_PUBLIC_URL', '')) if existing else None
    from waitress import create_server, wasyncore
    from waitress.task import ThreadedTaskDispatcher
    runtime = root / 'runtime'
    runtime.mkdir(exist_ok=True)
    address_file = runtime / 'mobile-url.txt'
    connections = {}
    dispatcher = ThreadedTaskDispatcher()
    dispatcher.set_thread_count(8)
    try:
        # Binding is synchronous: occupied ports fail before opening a tunnel.
        server = create_server(app, map=connections,
                               _dispatcher=dispatcher, host='127.0.0.1', port=port,
                               threads=8, max_request_body_size=32*1024*1024)
    except BaseException:
        wasyncore.close_all(connections, ignore_all=True)
        dispatcher.shutdown()
        raise
    worker = threading.Thread(target=server.run, daemon=True)
    process = None
    log = None
    try:
        address_file.unlink(missing_ok=True)
        worker.start()
        # Login status verifies that the authenticated application is responding.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f'http://127.0.0.1:{port}/api/auth/status', timeout=5) as response:
            import json
            state=json.load(response)
            if 'configured' not in state:raise RuntimeError('프로그램 로그인 상태 확인에 실패했습니다.')
        pending = None
        if not existing:
            print('[INFO] Cloudflare 주소를 생성하고 있습니다...', flush=True)
            log = (runtime / 'cloudflared.log').open('w', encoding='utf-8')
            process = subprocess.Popen(tunnel_command(executable, root, port), stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
            url, pending = wait_for_url(process, log=log)
        # CSRF validation must know the browser-facing origin. cloudflared may
        # forward a different Host to the private loopback server.
        app.config['AUTH_PUBLIC_ORIGIN'] = url
        address_file.write_text(url + '\n', encoding='utf-8')
        print(f'\nHaruLog v2.9.17 MOBILE URL: {url}\n'
              '휴대폰 브라우저에서 위 HTTPS 주소를 열고 프로그램에 로그인하세요.\n'
              '종료: Ctrl+C (현재 HaruLog 서버와 이번 실행에서 시작한 Quick Tunnel 종료)', flush=True)
        if not state.get('configured'):
            print(f'[최초 관리자 설정 링크] {url}/login#setup={app.config["AUTH_SETUP_TOKEN"]}\n다른 사람에게 공유하지 마세요.',flush=True)
        while worker.is_alive():
            if process is not None and process.poll() is not None:
                raise RuntimeError('Cloudflare 연결 프로세스가 종료되었습니다. 다시 실행해 주세요.')
            if pending is not None:
                # Discard already-logged messages without accumulating an unbounded queue.
                while True:
                    try:
                        if pending.get_nowait() is None:
                            raise RuntimeError('Cloudflare 출력 연결이 종료되었습니다.')
                    except queue.Empty:
                        break
            worker.join(0.25)
        raise RuntimeError('HaruLog 웹 서버가 종료되었습니다.')
    finally:
        stop_process(process)
        if process is not None:
            reader = getattr(process, '_harulog_reader', None)
            if reader is not None:
                reader.join(timeout=3)
            if process.stdout is not None:
                process.stdout.close()
        if log is not None:
            log.close()
        wasyncore.close_all(connections, ignore_all=True)
        dispatcher.shutdown()
        worker.join(timeout=3)
        address_file.unlink(missing_ok=True)
        print('[STOPPED] 현재 HaruLog 서버를 종료했습니다. 다른 프로그램의 터널은 유지합니다.',flush=True)
