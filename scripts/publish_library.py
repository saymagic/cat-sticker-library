#!/usr/bin/env python3
"""Build a public static library and preserve ZIP files as immutable Release assets."""
from __future__ import annotations

import argparse
import copy
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import quote, unquote, urlsplit
from urllib.request import urlopen

import sticker_library as lib

ROOT = Path(__file__).resolve().parents[1]


def config(root):
    value = lib.load(root / 'deployment/config.json')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', value['repository']):
        raise ValueError('Invalid repository')
    if not re.fullmatch(r'[a-z0-9.-]+', value['domain']) or value['public_url'] != 'https://' + value['domain'] + '/':
        raise ValueError('Invalid public domain')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', value['release_tag']):
        raise ValueError('Invalid release tag')
    return value


def prepare(root):
    settings = config(root)
    archives = {}
    for file in sorted(root.rglob('*.zip')):
        relative = file.relative_to(root)
        if relative.parts[0] in ('.git', '_site', 'deployment'):
            continue
        digest = lib.sha(file)
        asset = archives.setdefault(digest, {'sha256': digest, 'bytes': file.stat().st_size,
            'name': 'archive-' + digest + '.zip', 'tag': settings['release_tag'], 'paths': []})
        asset['paths'].append(relative.as_posix())
    if not archives:
        raise ValueError('No completed ZIP materials found')
    records = {'schema_version': 1, 'repository': settings['repository'], 'assets': list(archives.values())}
    old = root / 'deployment/archives.json'
    if old.is_file():
        known = {x['sha256']: x for x in lib.load(old)['assets']}
        for asset in records['assets']:
            if asset['sha256'] in known:
                asset['tag'] = known[asset['sha256']]['tag']
    lib.save(old, records)
    staging = root / 'deployment/staging' / settings['release_tag']
    staging.mkdir(parents=True, exist_ok=True)
    for asset in records['assets']:
        if asset['tag'] != settings['release_tag']:
            continue
        target = staging / asset['name']
        if not target.is_file() or lib.sha(target) != asset['sha256']:
            shutil.copy2(lib.inside(root, asset['paths'][0]), target)
    lib.save(staging / 'archives.json', records)
    return {'status': 'PASS', 'unique_archives': len(records['assets']),
        'original_paths': sum(len(x['paths']) for x in records['assets']),
        'bytes': sum(x['bytes'] for x in records['assets']), 'staging': str(staging)}


def archive_url(settings, asset):
    return 'https://github.com/' + settings['repository'] + '/releases/download/' + quote(asset['tag'], safe='') + '/' + asset['name']


def restore(root):
    settings = config(root); records = lib.load(root / 'deployment/archives.json')
    restored = 0
    with tempfile.TemporaryDirectory() as directory:
        for asset in records['assets']:
            present = next((lib.inside(root, p) for p in asset['paths'] if lib.inside(root, p).is_file()
                            and lib.sha(lib.inside(root, p)) == asset['sha256']), None)
            if present is None:
                present = Path(directory) / asset['name']
                if os.environ.get('GH_TOKEN'):
                    subprocess.run(['gh', 'release', 'download', asset['tag'], '--repo', settings['repository'],
                        '--pattern', asset['name'], '--dir', directory], check=True)
                else:
                    with urlopen(archive_url(settings, asset), timeout=60) as response, present.open('wb') as output:
                        shutil.copyfileobj(response, output)
                if present.stat().st_size != asset['bytes'] or lib.sha(present) != asset['sha256']:
                    raise ValueError('Release download failed integrity check: ' + asset['name'])
            for relative in asset['paths']:
                target = lib.inside(root, relative)
                if target.is_file():
                    if lib.sha(target) != asset['sha256']:
                        raise ValueError('Existing ZIP differs from manifest; preserving it: ' + relative)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(present, target); restored += 1
    return {'status': 'PASS', 'restored_paths': restored}


def inline(text):
    text = html.escape(text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    def link(match):
        value = html.unescape(match[2]).strip('<>')
        if urlsplit(value).scheme not in ('', 'http', 'https'):
            return match[1]
        if not urlsplit(value).scheme and value.split('#')[0].endswith('.md'):
            value = value.replace('.md', '.html')
        return '<a href="' + html.escape(value, quote=True) + '">' + match[1] + '</a>'
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, text)


def document(text, back):
    """Render our small Markdown handbook without allowing arbitrary HTML."""
    lines = text.splitlines(); blocks = []; i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('```'):
            code = []; i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code.append(lines[i]); i += 1
            blocks.append('<pre><code>' + html.escape('\n'.join(code)) + '</code></pre>')
        elif re.match(r'^#{1,6} ', line):
            level = len(line.split(' ')[0]); blocks.append(f'<h{level}>' + inline(line[level+1:]) + f'</h{level}>')
        elif line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                cells = [x.strip() for x in lines[i].strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', x) for x in cells):
                    rows.append('<tr>' + ''.join('<td>' + inline(x) + '</td>' for x in cells) + '</tr>')
                i += 1
            blocks.append('<div class="table"><table>' + ''.join(rows) + '</table></div>'); continue
        elif re.match(r'^[-*] ', line):
            items = []
            while i < len(lines) and re.match(r'^[-*] ', lines[i]):
                items.append('<li>' + inline(lines[i][2:]) + '</li>'); i += 1
            blocks.append('<ul>' + ''.join(items) + '</ul>'); continue
        elif line:
            blocks.append('<p>' + inline(line) + '</p>')
        i += 1
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>表情作品库 · 资料</title><style>body{max-width:900px;margin:35px auto;padding:0 24px;background:#f4f2ed;color:#30382e;font:16px/1.8 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}a{color:#415e40}h1{line-height:1.3}h2{margin-top:2em}code{background:#e8eee2;padding:2px 4px;border-radius:4px}pre{overflow:auto;padding:18px;border-radius:12px;background:#fffefa;font-size:13px}pre code{background:none;padding:0}table{border-collapse:collapse;width:100%;background:#fffefa}td{border:1px solid #dce0d6;padding:10px}.table{overflow:auto}p{overflow-wrap:anywhere}img{max-width:100%;height:auto}</style><a href="' + html.escape(back) + '">← 回到表情作品库</a><main>' + ''.join(blocks) + '</main></html>'


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.values = []

    def handle_starttag(self, tag, attrs):
        self.values.extend(v for k, v in attrs if k in ('href', 'src') and v)


def _build(root, output):
    settings = config(root); data = lib.load(root / lib.CATALOG); characters = lib.configuration(root)
    lib.validate_registry(root, data, characters)
    if output.resolve() == root.resolve() or output.resolve().is_relative_to(root / '01_作品'):
        raise ValueError('Build output must be separate from original materials')
    if output.exists() and any(output.iterdir()):
        if not (output / 'build.json').is_file():
            raise ValueError('Refusing to replace a directory not produced by this builder')
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    records = lib.load(root / 'deployment/archives.json')
    by_path = {path: asset for asset in records['assets'] for path in asset['paths']}
    entries = [lib.hydrate(root, entry, characters) for entry in data['entries']]
    for entry in entries:
        if entry['status'] == '本地成品' and not entry['can_download']:
            raise ValueError('Completed version has invalid evidence: ' + entry['id'])
    for group in {(e['character'], e['theme'], e['media']) for e in entries}:
        versions = [e for e in entries if (e['character'], e['theme'], e['media']) == group and not e['archived']]
        usable = [e for e in versions if e['can_download']]
        preferred = next((e for e in usable if e['current']), None) or max(usable or versions, key=lambda e:e['sequence'], default=None)
        for e in versions:e['default'] = preferred is e
    copied = set()
    def copy_file(relative):
        if not relative or relative in copied or urlsplit(relative).scheme:
            return relative
        source = lib.inside(root, relative)
        if not source.is_file():
            raise ValueError('Missing public file: ' + relative)
        copied.add(relative)
        destination = output / relative
        if source.suffix == '.md':
            destination = destination.with_suffix('.html')
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix == '.md':
            text = source.read_text(encoding='utf-8')
            def command_link(match):
                linked = (source.parent / html.unescape(match[2])).resolve()
                if not linked.is_relative_to(root):raise ValueError('Documentation link escapes library')
                return match[1] + 'https://github.com/' + settings['repository'] + '/blob/main/' + quote(linked.relative_to(root).as_posix(), safe='/') + match[3]
            text = re.sub(r'(\[[^\]]+\]\()([^)]*\.command)(\))', command_link, text)
            back = os.path.relpath(output / lib.PAGE, destination.parent)
            destination.write_text(document(text, back), encoding='utf-8')
        elif source.suffix == '.html':
            text = source.read_text(encoding='utf-8')
            def rewrite(match):
                value = match[2]
                if urlsplit(value).scheme or value.startswith('#'):
                    return match[0]
                linked = (source.parent / unquote(value.split('#')[0].split('?')[0])).resolve()
                if linked.suffix == '.zip' and linked.is_relative_to(root):
                    record = by_path.get(linked.relative_to(root).as_posix())
                    if record is None:raise ValueError('Preview ZIP missing from Release manifest')
                    return match[1] + archive_url(settings, record) + match[3]
                if linked.suffix == '.md':
                    return match[1] + value.replace('.md', '.html') + match[3]
                return match[0]
            text = re.sub(r'((?:src|href)=["\'])([^"\']+)(["\'])', rewrite, text)
            destination.write_text(text, encoding='utf-8')
        else:
            shutil.copy2(source, destination)
        if source.suffix == '.html':
            parser = Links(); parser.feed(source.read_text(encoding='utf-8'))
            for value in parser.values:
                if urlsplit(value).scheme or value.startswith('#'):continue
                path = (source.parent / unquote(value.split('#')[0].split('?')[0])).resolve()
                if not path.is_relative_to(root) or not path.is_file():
                    raise ValueError('Preview contains invalid local reference: ' + value)
                if path.suffix != '.zip':copy_file(path.relative_to(root).as_posix())
        return destination.relative_to(output).as_posix()
    for entry in entries:
        entry.setdefault('default', False)
        for key in ('cover', 'preview', 'copy', 'readme'):
            entry[key] = copy_file(entry.get(key))
        for item in entry['items']:item['image'] = copy_file(item.get('image'))
        for key, path in entry['extras'].items():entry['extras'][key] = copy_file(path)
        for report in entry['reports']:report['path'] = copy_file(report['path'])
        for package in entry['packages']:
            asset = by_path.get(package['path'])
            if not asset:
                raise ValueError('ZIP has not been prepared for publishing: ' + package['path'])
            package['path'] = archive_url(settings, asset)
            package['sha256'] = asset['sha256']
        for key in ('reference',):
            entry.pop(key, None)
    for path in ('作品库设计与规则.md', 'AGENTS.md', '00_官方调研/微信表情制作与投稿调研.md', 'deployment/部署与更新.md'):
        copy_file(path)
    payload = {'updated_at': lib.now().isoformat(), 'characters': list(characters['characters']), 'entries': entries}
    serialized = json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    template = (root / 'scripts/templates/library.html').read_text(encoding='utf-8')
    page = template.replace('__LIBRARY_DATA__', serialized)
    page = page.replace('作品库设计与规则.md', '作品库设计与规则.html').replace('AGENTS.md', 'AGENTS.html').replace('00_官方调研/微信表情制作与投稿调研.md', '00_官方调研/微信表情制作与投稿调研.html')
    page = page.replace('</head>', '<meta name="description" content="奶思、古德、范恩的中文猫咪表情作品库，支持检索、收藏、历史版本查看和上传物料下载。"><link rel="canonical" href="' + settings['public_url'] + '"></head>')
    (output / lib.PAGE).write_text(page, encoding='utf-8')
    (output / 'index.html').write_text(page, encoding='utf-8')
    (output / '.nojekyll').write_text('')
    (output / 'CNAME').write_text(settings['domain'] + '\n')
    (output / 'catalog.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    local_links = 0
    for page_file in output.rglob('*.html'):
        links = Links(); links.feed(page_file.read_text(encoding='utf-8'))
        for value in links.values:
            if urlsplit(value).scheme or value.startswith('#'):continue
            local_links += 1
            target = (page_file.parent / unquote(value.split('#')[0].split('?')[0])).resolve()
            if not target.is_relative_to(output) or not target.is_file():
                raise ValueError('Missing generated website link: ' + value)
    report = {'status': 'PASS', 'versions': len(entries), 'stickers': sum(len(e['items']) for e in entries),
        'files': sum(1 for p in output.rglob('*') if p.is_file()), 'bytes': sum(p.stat().st_size for p in output.rglob('*') if p.is_file()),
        'release_downloads': sum(len(e['packages']) for e in entries), 'local_links_checked': local_links, 'output': str(output)}
    revision = os.environ.get('GITHUB_SHA')
    if not revision and (root / '.git').exists():
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    report['source_commit'] = revision
    report['built_at'] = lib.now().isoformat()
    report['public_url'] = settings['public_url']
    report['workflow_run'] = ('https://github.com/' + settings['repository'] + '/actions/runs/' + os.environ['GITHUB_RUN_ID']
        if os.environ.get('GITHUB_RUN_ID') else None)
    (output / 'build.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


def build(root, output):
    output = output.resolve()
    if output == root.resolve() or output.is_relative_to(root / '01_作品'):
        raise ValueError('Build output must be separate from original materials')
    if output.exists() and (not output.is_dir() or (any(output.iterdir()) and not (output / 'build.json').is_file())):
        raise ValueError('Refusing to replace a directory not produced by this builder')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.sticker-site-', dir=output.parent) as directory:
        scratch = Path(directory)
        report = _build(root, scratch)
        report['output'] = str(output)
        (scratch / 'build.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        if output.exists():shutil.rmtree(output)
        os.replace(scratch, output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('command', choices=('prepare', 'restore', 'build'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(); root = args.root.resolve()
    result = {'prepare': lambda:prepare(root), 'restore': lambda:restore(root),
              'build': lambda:build(root, (args.output or root / '_site').resolve())}[args.command]()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':main()
