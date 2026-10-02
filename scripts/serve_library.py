#!/usr/bin/env python3
"""Launch a read-only loopback library site. --open is for human launchers."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen
import webbrowser

ROOT = Path(__file__).resolve().parents[1]


def belongs(port):
    try:
        with urlopen(f'http://127.0.0.1:{port}/' + quote('作品目录.json'), timeout=1) as response:
            observed = json.load(response)
        local = json.loads((ROOT / '作品目录.json').read_text())
        return observed.get('schema_version') == 2 and {e['id'] for e in observed['entries']} == {e['id'] for e in local['entries']}
    except (OSError, ValueError, KeyError, URLError):
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8769)
    parser.add_argument('--open', action='store_true')
    parser.add_argument('--serve', action='store_true')
    args = parser.parse_args()
    if args.serve:
        handler = partial(SimpleHTTPRequestHandler, directory=str(ROOT))
        try:
            server = ThreadingHTTPServer(('127.0.0.1', args.port), handler)
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        return
    if not belongs(args.port):
        log = ROOT / '99_记录/本地查看服务.log'
        log.parent.mkdir(exist_ok=True)
        with log.open('ab') as stream:
            process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--serve', '--port', str(args.port)], stdout=stream, stderr=stream, start_new_session=True)
        for _ in range(30):
            if belongs(args.port):
                break
            if process.poll() is not None:
                raise SystemExit(f'端口{args.port}已被其他服务使用，可传--port指定空闲端口。日志：{log}')
            time.sleep(.1)
        else:
            raise SystemExit(f'本地服务未启动成功，查看日志：{log}')
    url = f'http://127.0.0.1:{args.port}/' + quote('表情包作品库.html')
    print(url)
    if args.open:
        webbrowser.open(url)


if __name__ == '__main__':
    main()
