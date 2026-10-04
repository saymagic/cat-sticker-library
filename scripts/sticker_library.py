#!/usr/bin/env python3
"""Maintain a local sticker library. Use library.sh for the bundled image runtime."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import fcntl
import hashlib
import html
import io
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import quote
import uuid
import zipfile
from zoneinfo import ZoneInfo

CATALOG = '作品目录.json'
PAGE = '表情包作品库.html'
SCHEMA = 2
STATES = ('设计草稿', '制作中', '本地成品')
PLATFORM_STATES = ('未投稿', '已提交', '审核通过', '需修改')
LOCKED_METADATA = ('id', 'character', 'theme', 'title', 'description', 'media', 'count', 'sequence', 'date', 'path', 'reference', 'style', 'copy_exception')


def now():
    return datetime.now(ZoneInfo('Asia/Shanghai'))


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as temp:
        temp.write(content)
        temp.flush()
        os.fsync(temp.fileno())
        name = temp.name
    os.replace(name, path)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def inside(root, value):
    root = Path(root).resolve()
    p = Path(value)
    if not value or p.is_absolute() or '..' in p.parts:
        raise ValueError(f'必须使用库内相对路径：{value}')
    target = (root / p).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f'路径越出作品库：{value}')
    return target


def component(value):
    value = value.strip()
    if not value or value.startswith('.') or re.search(r'[/\\\x00-\x1f<>:"|?*]', value) or len(value) > 60:
        raise ValueError(f'目录名称无效：{value!r}')
    return value


def date(value):
    datetime.strptime(value, '%Y%m%d')
    if not re.fullmatch(r'\d{8}', value):
        raise ValueError('日期使用YYYYMMDD')
    return value


def href(value):
    return quote(value, safe='/._-')


def configuration(root):
    return load(root / 'scripts/library_config.json')


def canonical(config, value):
    for name, info in config['characters'].items():
        if value.strip() in [name, *info['aliases']]:
            return name
    raise ValueError('角色应为奶思、古德或范恩。灰虎斑猫归奶思；新增角色需先更新角色配置。')


def validate_registry(root, data, config):
    if data.get('schema_version') != SCHEMA or not isinstance(data.get('entries'), list):
        raise ValueError('登记表格式不匹配。首次运行init；不要手工覆盖登记表。')
    ids, paths, sequences, current = set(), set(), set(), set()
    for entry in data['entries']:
        cat, theme = entry['character'], entry['theme']
        if not re.fullmatch(r'pack-[a-f0-9]{12}', entry['id']) or type(entry['sequence']) is not int or entry['sequence'] < 1:
            raise ValueError('版本ID或序号无效')
        if cat not in config['characters'] or component(theme) != theme:
            raise ValueError(f'角色或主题不符合规则：{entry["id"]}')
        expected = f'v{entry["sequence"]:03d}_{date(entry["date"])}_{entry["media"]}{entry["count"]}张'
        parts = Path(entry['path']).parts
        if parts != ('01_作品', cat, theme, '版本', expected):
            raise ValueError(f'目录应为角色/主题/版本：{entry["path"]}')
        target = inside(root, entry['path'])
        if not target.is_dir():
            raise ValueError(f'缺少版本目录：{entry["path"]}')
        if entry['status'] not in STATES or entry['media'] not in ('静态', '动态') or entry['count'] not in config['allowed_counts']:
            raise ValueError(f'状态、类型或数量无效：{entry["id"]}')
        if not 1 <= len(entry['title']) <= 8 or re.search(r'[^\u4e00-\u9fff]', entry['title']):
            raise ValueError('投稿名称为1至8个汉字，主题内部名称可更长')
        if len(entry.get('description', '')) > 80:
            raise ValueError('介绍最多80个字')
        if not isinstance(entry['tags'], list) or not all(isinstance(x, str) and 0 < len(x) <= 20 for x in entry['tags']):
            raise ValueError('标签应为短字符串列表')
        if entry['platform']['state'] not in PLATFORM_STATES:
            raise ValueError('平台状态无效')
        if entry['platform']['state'] != '未投稿':
            evidence = entry['platform'].get('evidence')
            if not evidence or not inside(target, evidence).is_file():
                raise ValueError('平台状态必须附本版本内真实凭据')
        group = (cat, theme, entry['media'])
        sequence = (cat, theme, entry['sequence'])
        if entry['id'] in ids or entry['path'] in paths or sequence in sequences:
            raise ValueError('版本ID、路径或序号重复')
        ids.add(entry['id']); paths.add(entry['path']); sequences.add(sequence)
        if entry['current']:
            if group in current or entry['status'] != '本地成品' or entry['archived']:
                raise ValueError('每个角色/主题/类型仅有一个已完成的常用版')
            current.add(group)
        for section in config['sections']:
            if not (target / section).is_dir():
                raise ValueError(f'缺少{section}：{entry["path"]}')
        if not inside(root, entry['reference']).is_file():
            raise ValueError(f'缺少角色参考：{entry["reference"]}')
    actual = set()
    work = root / '01_作品'
    if work.exists():
        for cat_dir in work.iterdir():
            if cat_dir.name.startswith('.'):
                continue
            if not cat_dir.is_dir() or cat_dir.name not in config['characters']:
                raise ValueError(f'作品区出现未知角色或散落文件：{cat_dir.name}')
            for theme_dir in cat_dir.iterdir():
                if theme_dir.name.startswith('.') or theme_dir.name == 'README.md':
                    continue
                if not theme_dir.is_dir() or not (theme_dir / '版本').is_dir():
                    raise ValueError(f'主题目录无版本区：{theme_dir}')
                for version in (theme_dir / '版本').iterdir():
                    if not version.name.startswith('.'):
                        actual.add(version.relative_to(root).as_posix())
    if actual != paths:
        raise ValueError(f'存在未登记或缺失版本：{sorted(actual ^ paths)}')


def select_entry(root, data, value):
    for entry in data['entries']:
        if value == entry['id']:
            return entry
        candidate = Path(value)
        if candidate.is_absolute():
            if candidate.resolve() == inside(root, entry['path']):
                return entry
        elif value.rstrip('/') == entry['path']:
            return entry
    raise ValueError('没有找到该版本，请使用new返回的ID或路径')


def read_required(out, name):
    path = inside(out, name)
    if not path.is_file():
        raise ValueError(f'成品缺少{name}')
    return load(path)


def inspect_image(path, spec, dynamic=False):
    try:
        from PIL import Image
    except ImportError as error:
        raise ValueError('图片验收需要Pillow，请运行scripts/library.sh使用已配置的图像运行环境') from error
    with Image.open(path) as image:
        image.load()
        if list(image.size) != spec['size'] or image.format != spec['format'] or path.stat().st_size > spec['limit']:
            raise ValueError(f'尺寸、格式或体积不合规：{path.name}')
        frames = getattr(image, 'n_frames', 1)
        if dynamic and (frames < 2 or image.info.get('loop') != 0):
            raise ValueError(f'动态主图需要真实多帧与无限循环：{path.name}')
        if not dynamic and frames != 1:
            raise ValueError(f'静态素材混入多帧图：{path.name}')
        for frame in range(frames):
            image.seek(frame)
            alpha = image.convert('RGBA').getchannel('A')
            if spec['alpha']:
                if alpha.getextrema() != (0, 255) or any(alpha.getpixel(p) for p in ((0, 0), (image.width-1, 0), (0, image.height-1), (image.width-1, image.height-1))):
                    raise ValueError(f'真实透明通道或透明角有误：{path.name}第{frame+1}帧')
                bbox = alpha.point(lambda a: 255 if a >= 8 else 0).getbbox()
                if not bbox or min(bbox[0], bbox[1], image.width-bbox[2], image.height-bbox[3]) < 2:
                    raise ValueError(f'画面留边不足：{path.name}')
            elif alpha.getextrema() != (255, 255):
                raise ValueError(f'横幅须有不透明背景：{path.name}')


def acceptance(root, entry):
    """Verify evidence, actual files and archives; never manufacture a visual verdict."""
    version = inside(root, entry['path']); out = version / '04_成品'
    manifest = read_required(out, 'manifest.json')
    report = read_required(out, 'validation_report.json')
    visual = read_required(out, 'visual_review.json')
    profile = read_required(out, 'platform-profile.json')
    packages = read_required(out, 'zip_validation.json')
    job = read_required(out, 'job.json')
    expected = [f'{i:02d}' for i in range(1, entry['count']+1)]
    if not isinstance(manifest, list) or [item['number'] for item in manifest] != expected:
        raise ValueError('主图数量与连续编号应符合登记张数')
    if job.get('characters') != [entry['character']] or job.get('title') != entry['title']:
        raise ValueError('工程中的角色或专辑名称与登记不一致')
    if job.get('description') != entry.get('description'):
        raise ValueError('专辑介绍与登记不一致，请在完成前对齐')
    if [x.get('caption') for x in job.get('items', [])] != [x['caption'] for x in manifest]:
        raise ValueError('工程文案与成品清单顺序不一致')
    if not entry.get('description') or len(entry['description']) > 80:
        raise ValueError('完成前填写80字以内的专辑介绍')
    meanings = []
    for item in manifest:
        caption, meaning = item['caption'], item['meaning']
        if not caption or not isinstance(caption, str) or item['characters'] != [entry['character']]:
            raise ValueError('每张都要有文案，且仅包含本套角色')
        if not entry.get('copy_exception') and (not re.search(r'[\u4e00-\u9fff]', caption) or re.search(r'[A-Za-z]', caption)):
            raise ValueError(f'默认文案全中文：{caption}')
        if not isinstance(meaning, str) or not 1 <= len(meaning) <= 4:
            raise ValueError('含义词为1至4字')
        meanings.append(meaning)
        if not inside(out, item['source']).is_file():
            raise ValueError(f'原画来源缺失：{item["number"]}')
        if not (version / '02_原画' / f'{item["number"]}.png').is_file():
            raise ValueError(f'版本原画缺失：{item["number"]}')
    if len(set(meanings)) != len(meanings):
        raise ValueError('同套含义词不得重复')
    if not report.get('technical_pass') or not report.get('checks') or not all(c.get('pass') is True for c in report['checks']):
        raise ValueError('技术验收未通过')
    if not profile.get('official_rules_verified') or not profile.get('basis_date'):
        raise ValueError('缺少本次核对的官方规则快照')
    if profile['basis_date'].replace('-', '') < entry['date']:
        raise ValueError('规格快照早于本次创作，请先核对并记录当前规则')
    assets = report.get('assets', [])
    hashes = {x['file']: x['sha256'] for x in assets}
    if len(hashes) != len(assets) or not hashes:
        raise ValueError('技术报告的素材哈希清单无效')
    for asset in assets:
        path = inside(out, asset['file'])
        if not path.is_file() or sha(path) != asset['sha256']:
            raise ValueError(f'素材与已验收报告不一致：{asset["file"]}')
    fields = ('identity', 'anatomy', 'caption', 'outline', 'pose', 'readability')
    items = visual.get('items', [])
    if visual.get('status') != 'passed' or not visual.get('reviewer') or visual.get('issues') != [] or [x.get('number') for x in items] != expected:
        raise ValueError('缺少逐张视觉复核，技术检查不能代替目检')
    if not all(all(item.get(field) is True for field in fields) for item in items):
        raise ValueError('逐张视觉复核有未完成项')
    if entry['media'] == '动态' and not all(x.get('motion') is True and x.get('loop') is True for x in items):
        raise ValueError('动态图还须逐张目检动作与循环接缝')
    if not set(('light', 'dark', 'checker')).issubset(visual.get('background_modes', [])) or 240 not in visual.get('actual_size_px', []):
        raise ValueError('视觉记录须包含240px实际大小和三种底色')
    if visual.get('asset_sha256') != hashes or not all(visual.get('extras', {}).get(key) is True for key in ('cover', 'chat_icon', 'banner')):
        raise ValueError('视觉记录与素材不一致，或配套图片未复核')
    primary = 'main_png' if entry['media'] == '静态' else 'main_gif'
    for item in manifest:
        path = inside(out, item[primary])
        if item[primary] not in hashes:
            raise ValueError('主图未纳入技术报告')
        inspect_image(path, profile[primary], entry['media'] == '动态')
        if entry['media'] == '静态' and item.get('main_gif'):
            inspect_image(inside(out, item['main_gif']), profile['main_gif'])
        if item.get('thumbnail'):
            inspect_image(inside(out, item['thumbnail']), profile['thumbnail'])
    if len({sha(inside(out, x[primary])) for x in manifest}) != len(manifest):
        raise ValueError('同套出现完全相同的主图')
    for key in ('cover', 'chat_icon', 'banner'):
        spec = profile['extras'][key]
        asset = 'extras/' + spec['file']
        if asset not in hashes:
            raise ValueError(f'{key}未纳入技术报告')
        inspect_image(inside(out, asset), spec)
    for required in ('preview.html', '上传填写文案.md', 'captions.csv'):
        if not (out / required).is_file():
            raise ValueError(f'缺少{required}')
    with (out / 'captions.csv').open(encoding='utf-8-sig', newline='') as stream:
        copy_rows = list(csv.DictReader(stream))
    if [(x.get('number'), x.get('caption'), x.get('meaning')) for x in copy_rows] != [(x['number'], x['caption'], x['meaning']) for x in manifest]:
        raise ValueError('填写文案CSV与成品清单不一致')
    for link in re.findall(r'(?:src|href)="([^"]+)"', (out / 'preview.html').read_text()):
        if not link.startswith(('http:', 'https:', '#', 'data:')) and not inside(out, link.split('#')[0]).is_file():
            raise ValueError(f'单套预览有断链：{link}')
    required_packages = {'complete_delivery.zip', 'submission_PNG.zip' if entry['media'] == '静态' else 'submission_GIF.zip'}
    if not required_packages.issubset({x['file'] for x in packages}):
        raise ValueError('缺少投稿包或完整制作备份')
    for record in packages:
        path = inside(out, record['file'])
        if not path.is_file() or sha(path) != record['sha256']:
            raise ValueError(f'ZIP与验收记录不一致：{record["file"]}')
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if archive.testzip() or len(names) != len(set(names)) or any(n.startswith(('/', '\\')) or '..' in Path(n.replace('\\', '/')).parts for n in names):
                raise ValueError(f'ZIP损坏、重名或路径越界：{path.name}')
            if path.name.startswith('submission_'):
                packaged = json.loads(archive.read('manifest.json'))
                if [x['number'] for x in packaged] != expected or [x['caption'] for x in packaged] != [x['caption'] for x in manifest]:
                    raise ValueError('投稿包清单与当前版本不符')
                if any(n.startswith(('sources/', 'masters/', 'layers/', 'scripts/')) for n in names):
                    raise ValueError('投稿包混入制作原画或工程')
                for original, packed in zip(manifest, packaged):
                    kind = 'main_png' if packed['main'].lower().endswith('.png') else 'main_gif'
                    if packed['main'] not in names or hashlib.sha256(archive.read(packed['main'])).hexdigest() != sha(inside(out, original[kind])):
                        raise ValueError('投稿包中的主图与成品不符')
                    if original.get('thumbnail'):
                        thumb = packed['thumbnail']
                        if thumb not in names or hashlib.sha256(archive.read(thumb)).hexdigest() != sha(inside(out, original['thumbnail'])):
                            raise ValueError('投稿包中的缩略图与成品不符')
                for key in ('cover', 'chat_icon', 'banner'):
                    asset = 'extras/' + profile['extras'][key]['file']
                    if asset not in names or hashlib.sha256(archive.read(asset)).hexdigest() != sha(inside(out, asset)):
                        raise ValueError('投稿包中的配套素材与成品不符')
            elif path.name == 'complete_delivery.zip':
                required = {'manifest.json', 'job.json', 'platform-profile.json', 'validation_report.json', 'visual_review.json', 'preview.html', '上传填写文案.md', 'captions.csv', *hashes, *[x['source'] for x in manifest]}
                if not required.issubset(names):
                    raise ValueError('完整备份缺少原画、成品或验收材料')
                for asset in required - {'preview.html'}:
                    if hashlib.sha256(archive.read(asset)).hexdigest() != sha(inside(out, asset)):
                        raise ValueError('完整备份内容与本版本不一致：' + asset)
            for name in (n for n in names if n.endswith('.html')):
                for link in re.findall(r'(?:src|href)="([^"]+)"', archive.read(name).decode('utf-8')):
                    if not link.startswith(('http:', 'https:', '#', 'data:')) and (Path(name).parent / link.split('#')[0]).as_posix() not in names:
                        raise ValueError('ZIP内预览引用失效')
    return {'technical_checks': len(report['checks']), 'visual_items': len(items), 'assets': len(assets), 'packages': len(packages), 'profile_date': profile['basis_date']}


def protected_files(version):
    for folder in ('01_资料', '02_原画', '03_工程', '04_成品'):
        for path in sorted((version / folder).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.name not in ('.DS_Store', '作品信息.json', 'README.md'):
                yield path


def seal_version(root, entry, gate):
    version = inside(root, entry['path'])
    files = []
    for path in protected_files(version):
        stat = path.stat()
        files.append({'file': path.relative_to(version).as_posix(), 'sha256': sha(path), 'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns})
    seal = {'version_id': entry['id'], 'completed_at': now().isoformat(), 'metadata': {key: entry.get(key) for key in LOCKED_METADATA}, 'scope': '已交付的资料、原画、工程和成品；生成的导航及后续平台凭据另行维护', 'gate': gate, 'files': files}
    path = version / '05_验收/完成锁定.json'
    save(path, seal)
    entry['completion'] = {'seal': '05_验收/完成锁定.json', 'sha256': sha(path), 'completed_at': seal['completed_at'], 'gate': gate}


def integrity(root, entry, deep=False):
    if entry['status'] != '本地成品':
        return {'state': '未完成', 'issues': [], 'checked': 0}
    version = inside(root, entry['path']); completed = entry.get('completion') or {}
    issues = []
    try:
        path = inside(version, completed['seal'])
        if sha(path) != completed['sha256']:
            raise ValueError('完成锁定记录已改变')
        sealed = load(path)
        if sealed['version_id'] != entry['id']:
            raise ValueError('完成锁定记录属于其他版本')
        if sealed.get('metadata') != {key: entry.get(key) for key in LOCKED_METADATA}:
            issues.append('交付后的角色、主题、文案资料、参考或画风登记有改变，须创建新版本')
        expected = {x['file'] for x in sealed['files']}
        actual = {p.relative_to(version).as_posix() for p in protected_files(version)}
        if expected != actual:
            issues.append('原始制作文件有新增或缺失，须作为新版本复检')
        for item in sealed['files']:
            asset = inside(version, item['file'])
            if not asset.is_file():
                issues.append('缺失：' + item['file']); continue
            stat = asset.stat()
            if stat.st_size != item['bytes']:
                issues.append('交付后改变：' + item['file'])
            elif (deep or stat.st_mtime_ns != item['mtime_ns']) and sha(asset) != item['sha256']:
                issues.append('哈希改变：' + item['file'])
            if deep and asset.suffix == '.zip':
                with zipfile.ZipFile(asset) as archive:
                    if archive.testzip():
                        issues.append('ZIP完整性失败：' + item['file'])
        return {'state': '需复检' if issues else '有效', 'issues': issues, 'checked': len(expected), 'mode': '完整哈希与ZIP' if deep else '文件大小与修改时间'}
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as error:
        return {'state': '需复检', 'issues': [str(error)], 'checked': 0}


def set_current(data, entry):
    for other in data['entries']:
        if (other['character'], other['theme'], other['media']) == (entry['character'], entry['theme'], entry['media']):
            other['current'] = other['id'] == entry['id']


def audit(root, command, ids):
    path = root / '99_记录/维护日志.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps({'time': now().isoformat(), 'command': command, 'version_ids': ids}, ensure_ascii=False) + '\n')


def mirror(root, entry):
    version = inside(root, entry['path'])
    if not entry.get('completion'):
        # Git does not preserve empty directories in unfinished versions.
        for section in configuration(root)['sections']:
            marker = version / section / '.gitkeep'
            if not marker.exists():
                save(marker, '')
    save(version / '01_资料/作品信息.json', {'source': '根目录作品目录.json，由维护工具生成，请勿手工修改', **entry})
    relative = os.path.relpath(root / PAGE, version)
    save(version / 'README.md', f'# {entry["character"]} · {entry["theme"]} · v{entry["sequence"]:03d}\n\n[回到统一作品库]({href(relative)})\n\n状态以根目录作品目录.json及完成锁定检查为准。\n\n' + '\n'.join(f'- `{section}/`' for section in ('01_资料', '02_原画', '03_工程', '04_成品', '05_验收')) + '\n')


def hydrate(root, entry, config):
    version = inside(root, entry['path']); out = version / '04_成品'
    health = integrity(root, entry)
    result = {**entry, 'health': health, 'display_status': '需复检' if health['state'] == '需复检' else entry['status'], 'items': [], 'packages': [], 'reports': []}
    def link(path):
        return path.relative_to(root).as_posix() if path.is_file() else None
    result['cover'] = link(out / 'extras/cover_240.png') or entry['reference']
    result['preview'] = link(out / 'preview.html')
    result['copy'] = link(out / '上传填写文案.md')
    result['readme'] = link(version / 'README.md')
    for key, name in (('cover', 'cover_240.png'), ('chat_icon', 'chat_icon_50.png'), ('banner', 'banner_750x400.jpg')):
        result.setdefault('extras', {})[key] = link(out / 'extras' / name)
    manifest = load(out / 'manifest.json') if (out / 'manifest.json').is_file() else []
    if not manifest and (version / '01_资料/文案.csv').is_file():
        with (version / '01_资料/文案.csv').open(encoding='utf-8-sig', newline='') as stream:
            for row in csv.DictReader(stream):
                number = row.get('number', row.get('编号'))
                if not number:
                    raise ValueError(f'草稿文案CSV缺少编号列：{entry["path"]}/01_资料/文案.csv')
                manifest.append({'number': str(number).zfill(2),
                                 'caption': row.get('caption', row.get('中文文案', '')),
                                 'meaning': row.get('meaning', row.get('含义词', ''))})
    for item in manifest:
        image = item.get('main_png') if entry['media'] == '静态' else item.get('main_gif')
        result['items'].append({'number': item['number'], 'caption': item.get('caption', ''), 'meaning': item.get('meaning', ''), 'image': link(inside(out, image)) if image else None})
    if (out / 'zip_validation.json').is_file():
        for package in load(out / 'zip_validation.json'):
            path = inside(out, package['file'])
            label = '完整制作备份' if package['file'] == 'complete_delivery.zip' else 'PNG上传包' if 'PNG' in package['file'] else 'GIF上传包' if entry['media'] == '动态' else 'GIF静态备用'
            if path.is_file():
                result['packages'].append({'path': link(path), 'label': label, 'bytes': path.stat().st_size, 'download': f'{entry["character"]}_{entry["theme"]}_v{entry["sequence"]:03d}_{package["file"]}'})
    for label, path in (('技术检查', out / 'validation_report.json'), ('逐张目检', out / 'visual_review.json'), ('ZIP检查', out / 'zip_validation.json'), ('完成锁定', version / '05_验收/完成锁定.json')):
        if path.is_file():
            result['reports'].append({'label': label, 'path': link(path)})
    result['aliases'] = config['characters'][entry['character']]['aliases']
    result['identity'] = config['characters'][entry['character']]['identity']
    result['can_download'] = entry['status'] == '本地成品' and health['state'] == '有效'
    return result


def refresh(root, data, config):
    validate_registry(root, data, config)
    for e in data['entries']:
        mirror(root, e)
    entries = [hydrate(root, e, config) for e in data['entries']]
    for group in {(e['character'], e['theme'], e['media']) for e in entries}:
        versions = [e for e in entries if (e['character'], e['theme'], e['media']) == group and not e['archived']]
        usable = [e for e in versions if e['can_download']]
        preferred = next((e for e in usable if e['current']), None) or max(usable or versions, key=lambda e: e['sequence'], default=None)
        for e in versions:
            e['default'] = preferred is e
    for e in entries:
        e.setdefault('default', False)
    data['updated_at'] = now().isoformat()
    save(root / CATALOG, data)
    payload = {'updated_at': data['updated_at'], 'characters': list(config['characters']), 'entries': entries}
    serialized = json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    template = (root / 'scripts/templates/library.html').read_text()
    save(root / PAGE, template.replace('__LIBRARY_DATA__', serialized))
    save(root / 'index.html', '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=表情包作品库.html"><title>表情包作品库</title><a href="表情包作品库.html">打开统一作品库</a></html>')
    tables = ['| 角色 | 主题 | 版本 | 本地状态 | 微信状态 |', '| --- | --- | --- | --- | --- |']
    for e in entries:
        tables.append(f'| {e["character"]} | {e["theme"]} | v{e["sequence"]:03d}{" · 常用" if e["current"] else ""} | {e["display_status"]} | {e["platform"]["state"]} |')
    online = ''
    if (root / 'deployment/config.json').is_file():
        deployment = load(root / 'deployment/config.json')
        online = f'[公开作品库]({deployment["public_url"]}) · [GitHub仓库](https://github.com/{deployment["repository"]}) · [部署与更新](deployment/部署与更新.md)\n\n'
    save(root / 'README.md', '# 表情包作品库\n\n' + online + '[查看统一作品库](表情包作品库.html) · [一键启动入口](打开作品库.command) · [系统与存放规则](作品库设计与规则.md) · [给后续创作代理的约束](AGENTS.md)\n\n按套查看、逐图中文检索、角色/类型/状态筛选、历史版本、收藏与下载。日常双击打开作品库.command，自动刷新并打开本地网页。\n\n' + '\n'.join(tables) + '\n\n后续直接用中文描述新创作、续作或修改，代理负责建版本、登记、验收与更新入口。维护命令见系统与存放规则。\n\n本地成品与微信审核状态分别记录；新草稿不会替换常用成品。收藏保存在当前浏览器中。\n')
    links = []
    for e in entries:
        links += [e.get(x) for x in ('cover', 'preview', 'copy', 'readme')]
        links += [x['image'] for x in e['items']]
        links += [x['path'] for x in [*e['packages'], *e['reports']]]
        links += list(e['extras'].values())
    missing = [x for x in filter(None, links) if not inside(root, x).is_file()]
    save(root / '99_记录/作品库链接检查.json', {'status': 'FAIL' if missing else 'PASS', 'checked': len([x for x in links if x]), 'missing': missing})
    issues = [{'id': e['id'], 'issues': e['health']['issues']} for e in entries if e['health']['issues']]
    return {'status': 'FAIL' if issues or missing else 'PASS', 'themes': len({(e['character'], e['theme']) for e in entries}), 'versions': len(entries), 'stickers': sum(len([x for x in e['items'] if x['image']]) for e in entries), 'issues': issues, 'page': str(root / PAGE)}


def new_entry(root, data, config, args):
    cat, theme = canonical(config, args.cat), component(args.theme)
    title = args.title or theme
    if not 1 <= len(title) <= 8 or re.search(r'[^\u4e00-\u9fff]', title):
        raise ValueError('投稿名称1至8个汉字；长主题请另传--title')
    if args.count not in config['allowed_counts']:
        raise ValueError('专辑张数为8至24；默认24张')
    if len(args.description or '') > 80:
        raise ValueError('介绍最多80个字')
    if args.tag and not all(0 < len(tag) <= 20 for tag in args.tag):
        raise ValueError('每个标签1至20个字')
    source = inside(root, args.reference or config['characters'][cat]['reference'])
    if not source.is_file():
        raise ValueError('角色参考不存在，创建版本前先整理参考')
    stamp = date(args.date or now().strftime('%Y%m%d'))
    sequence = max((e['sequence'] for e in data['entries'] if (e['character'], e['theme']) == (cat, theme)), default=0) + 1
    relative = f'01_作品/{cat}/{theme}/版本/v{sequence:03d}_{stamp}_{args.type}{args.count}张'
    target = inside(root, relative)
    target.mkdir(parents=True, exist_ok=False)
    for folder in config['sections']:
        (target / folder).mkdir()
    reference = target / '01_资料/参考/卡通基准.png'
    reference.parent.mkdir()
    reference.write_bytes(source.read_bytes())
    entry = dict(id='pack-' + uuid.uuid4().hex[:12], character=cat, theme=theme, title=title,
                 media=args.type, count=args.count, sequence=sequence, date=stamp, status='设计草稿' if getattr(args, 'draft', False) else '制作中', current=False,
                 archived=False, path=relative, reference=reference.relative_to(root).as_posix(),
                 tags=args.tag or config['default_tags'], description=args.description or '', style=config['style_default'],
                 copy_exception=args.copy_exception or '', created_at=now().isoformat(), platform={'state': '未投稿', 'evidence': None}, completion=None)
    stream = io.StringIO(); writer = csv.writer(stream)
    writer.writerow(['number', 'caption', 'meaning'])
    writer.writerows((f'{i:02d}', '', '') for i in range(1, args.count+1))
    save(target / '01_资料/文案.csv', '\ufeff' + stream.getvalue())
    save(target / '01_资料/创作需求.md', f'# {cat} · {theme}\n\n投稿名称：{title}\n\n角色特征：{config["characters"][cat]["identity"]}\n\n类型：{args.type}，{args.count}张。文案按文案.csv逐张编号；默认全中文。\n\n画风：{entry["style"]}\n\n参考：参考/卡通基准.png。来源与权利按真实情况记录。\n\n本次需求、文字颜色、动作和用户修订请补充在这里。\n')
    if inside(root, config['platform_profile']).is_file():
        profile = load(inside(root, config['platform_profile']))
        if profile.get('basis_date', '').replace('-', '') != stamp:
            profile['official_rules_verified'] = False
            profile['note'] = '继承的规格参考，须为本次创作重新核对官方公开规范后更新日期与确认标记。'
        save(target / '03_工程/platform-profile.json', profile)
    data['entries'].append(entry)
    return entry


def initialize(root, config):
    old = load(root / CATALOG) if (root / CATALOG).exists() else {'works': []}
    if old.get('schema_version') == SCHEMA:
        raise ValueError('作品库已经初始化，使用refresh或new')
    data = {'schema_version': SCHEMA, 'timezone': 'Asia/Shanghai', 'entries': []}
    for work in old.get('works', []):
        target = inside(root, work['path']); out = target / '04_成品'; job = load(out / 'job.json')
        match = re.fullmatch(r'v(\d+)_(\d{8})_(静态|动态)(\d+)张', target.name)
        if not match:
            raise ValueError('旧版本目录名不兼容，请保留原库并单独登记迁移映射')
        for section in config['sections']:
            (target / section).mkdir(exist_ok=True)
        ref = out / 'production/用户原始卡通参考.png'
        if not ref.is_file():
            ref = inside(root, work['original_reference'])
        entry = dict(id='pack-' + uuid.uuid4().hex[:12], character=canonical(config, work['character']), theme=work['theme'],
                     title=job['title'], description=job.get('description', ''), media=match[3], count=int(match[4]),
                     sequence=int(match[1]), date=match[2], status='制作中', current=False, archived=False,
                     path=work['path'], reference=ref.relative_to(root).as_posix(), tags=job.get('tags', config['default_tags']),
                     style='原始卡通基准、中文在上、猫咪在下、主图白色贴纸外沿', copy_exception='',
                     created_at=match[2], platform={'state': '未投稿', 'evidence': None}, completion=None)
        gate = acceptance(root, entry)
        seal_version(root, entry, gate)
        entry['status'] = '本地成品'; entry['current'] = True
        data['entries'].append(entry)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init', help='首次接入已有三套；不重画、不改已交付图片')
    create = sub.add_parser('new', help='创建下一版本并自动登记')
    create.add_argument('--cat', required=True); create.add_argument('--theme', required=True)
    create.add_argument('--type', choices=('静态', '动态'), default='静态'); create.add_argument('--count', type=int, default=24)
    create.add_argument('--date'); create.add_argument('--title'); create.add_argument('--description')
    create.add_argument('--tag', action='append'); create.add_argument('--reference')
    create.add_argument('--copy-exception', help='仅记录用户明确要求非中文文案的原话')
    create.add_argument('--draft', action='store_true', help='先登记文案策划草稿')
    done = sub.add_parser('finish', help='检验真实文件和记录后锁定本地成品')
    done.add_argument('--path', required=True); done.add_argument('--current', action='store_true')
    sub.add_parser('refresh', help='刷新统一作品库，不创建新版本')
    verify = sub.add_parser('check', help='检查结构、登记、完成锁定与链接')
    verify.add_argument('--deep', '--archives', action='store_true', help='复算所有交付文件SHA256并校验ZIP，耗时与库大小有关')
    preferred = sub.add_parser('prefer', help='把已验证的成品设为常用入口')
    preferred.add_argument('--path', required=True)
    stage = sub.add_parser('stage', help='更新未完成版本的策划或制作状态')
    stage.add_argument('--path', required=True); stage.add_argument('--state', choices=('设计草稿', '制作中'), required=True)
    edit = sub.add_parser('describe', help='更新检索资料，已完成作品仅允许改标签')
    edit.add_argument('--path', required=True); edit.add_argument('--tag', action='append'); edit.add_argument('--description')
    stage = sub.add_parser('platform', help='凭真实记录更新微信审核状态')
    stage.add_argument('--path', required=True); stage.add_argument('--state', choices=PLATFORM_STATES, required=True); stage.add_argument('--evidence')
    archive = sub.add_parser('archive', help='从常用视图收起版本，保留所有文件')
    archive.add_argument('--path', required=True); archive.add_argument('--restore', action='store_true')
    args = parser.parse_args(); root = args.root.resolve()
    try:
        config = configuration(root)
        with (root / '.sticker-library.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if args.command == 'init':
                data = initialize(root, config)
                if (root / CATALOG).exists():
                    save(root / '99_记录/20261002_作品库升级/升级前作品目录.json', load(root / CATALOG))
            else:
                data = load(root / CATALOG)
                validate_registry(root, data, config)
            changed = []
            if args.command == 'new':
                e = new_entry(root, data, config, args); changed = [e['id']]
            if args.command in ('finish', 'prefer', 'describe', 'platform', 'archive', 'stage'):
                e = select_entry(root, data, args.path); changed = [e['id']]
                if args.command == 'finish':
                    if e.get('completion'):
                        raise ValueError('已锁定的交付须创建新版本，不能重写同一版')
                    if e['archived']:
                        raise ValueError('先恢复归档版本后再完成入库')
                    gate = acceptance(root, e); seal_version(root, e, gate)
                    e['status'] = '本地成品'
                    if args.current or not any(x['current'] and (x['character'], x['theme'], x['media']) == (e['character'], e['theme'], e['media']) for x in data['entries']):
                        set_current(data, e)
                elif args.command == 'prefer':
                    if e['archived'] or e['status'] != '本地成品' or integrity(root, e, True)['state'] != '有效':
                        raise ValueError('常用入口必须是未归档且完整验收有效的本地成品')
                    set_current(data, e)
                elif args.command == 'stage':
                    if e.get('completion'):
                        raise ValueError('已完成版本不能退回草稿，修改请建新版本')
                    e['status'] = args.state
                elif args.command == 'describe':
                    if args.tag is not None: e['tags'] = args.tag
                    if args.description is not None:
                        if e.get('completion'): raise ValueError('已交付专辑介绍变化须创建新版本；标签可直接更新')
                        e['description'] = args.description
                elif args.command == 'platform':
                    if args.state != '未投稿':
                        if not e.get('completion') or not args.evidence or not inside(inside(root, e['path']), args.evidence).is_file():
                            raise ValueError('平台状态需要已完成版本和本版本内真实凭据')
                    e['platform'] = {'state': args.state, 'evidence': args.evidence, 'recorded_at': now().isoformat()}
                elif args.command == 'archive':
                    e['archived'] = not args.restore
                    if e['archived']: e['current'] = False
            validate_registry(root, data, config)
            if args.command == 'check':
                statuses = [{'id': e['id'], **integrity(root, e, args.deep)} for e in data['entries']]
                issues = [x for x in statuses if x['issues']]
                result = {'status': 'FAIL' if issues else 'PASS', 'versions': len(statuses), 'checks': statuses, 'mode': '完整哈希与ZIP' if args.deep else '快速'}
                save(root / '99_记录/作品库验收.json', result)
                if issues: raise ValueError(json.dumps(issues, ensure_ascii=False))
            else:
                result = refresh(root, data, config)
                if args.command != 'refresh': audit(root, args.command, changed)
                if args.command == 'new': result.update(id=e['id'], created=str(inside(root, e['path'])))
                if result['status'] != 'PASS': raise ValueError(json.dumps(result, ensure_ascii=False))
            print(json.dumps(result, ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        parser.exit(1, f'错误：{error}\n')


if __name__ == '__main__':
    main()
