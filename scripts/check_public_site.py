#!/usr/bin/env python3
"""Read-only HTTPS acceptance: compare the live site with its local build byte for byte."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.parse import quote
from urllib.request import urlopen

import publish_library as pub
import sticker_library as lib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=pub.ROOT)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args(); root = args.root.resolve(); site = root / '_site'
    settings = pub.config(root)
    def read(relative):
        with urlopen(settings['public_url'] + quote(relative, safe='/'), timeout=30) as response:
            if response.status != 200:raise ValueError('HTTP status is not 200: ' + relative)
            return response.read()
    online_build = json.loads(read('build.json'))
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    if online_build.get('source_commit') != revision:
        raise ValueError('Public build does not match current source commit')
    files = [p for p in site.rglob('*') if p.is_file() and not p.name.startswith('.') and p.name != 'CNAME']
    def check(file):
        relative = file.relative_to(site).as_posix()
        try:
            data = read(relative); digest = hashlib.sha256(data).hexdigest()
            return {'path': relative, 'bytes': len(data), 'sha256': digest,
                'pass': digest == lib.sha(file)}
        except Exception as error:
            return {'path': relative, 'pass': False, 'error': str(error)}
    with ThreadPoolExecutor(max_workers=6) as pool:results = list(pool.map(check, files))
    errors = [r for r in results if not r['pass']]
    report = {'status': 'FAIL' if errors else 'PASS', 'verified_at': lib.now().isoformat(),
        'url': settings['public_url'], 'source_commit': revision, 'https_certificate_validation': True,
        'files_checked': len(results), 'files_passed': len(results) - len(errors),
        'build': online_build, 'results': results}
    if args.report:lib.save(args.report, report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('results','build')}, ensure_ascii=False))
    if errors:
        print(json.dumps(errors, ensure_ascii=False)); raise SystemExit(1)


if __name__ == '__main__':main()
