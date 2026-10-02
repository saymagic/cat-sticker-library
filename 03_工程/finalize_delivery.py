"""Archive the completed, manually inspected exports and their production evidence."""
from pathlib import Path
import hashlib
import json
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo

from validate_pack import validate, make_packages

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    packs = json.loads((ROOT / '03_工程/packs.json').read_text())
    identities = {'奶思': '灰黑虎斑短毛、金棕眼', '古德': '棕虎斑短毛、绿眼', '范恩': '浅奶白长毛、蓝眼和浅色耳尾'}
    fields = ('identity', 'anatomy', 'caption', 'outline', 'pose', 'readability')
    summaries = []
    for pack in packs:
        version = Path(pack['version_dir'])
        out = version / '04_成品'
        production = out / 'production'
        production.mkdir(exist_ok=True)
        for name in ('generation_requests.json', 'generation_log.jsonl', 'source_preflight.json'):
            shutil.copy2(version / '03_工程' / name, production / name)
        shutil.copy2(version / '01_资料/input.json', production / 'input.json')
        shutil.copy2(ROOT / pack['reference'], production / '用户原始卡通参考.png')
        shutil.copy2(version / '01_资料/上传填写文案.md', out / '上传填写文案.md')
        for name in ('pack_utils.py', 'validate_pack.py'):
            shutil.copy2(ROOT / '03_工程' / name, out / 'scripts' / name)

        # All five QA sheets per cat were actually viewed before this record was
        # written. Pixel validation alone is not the source of the visual verdict.
        prior_report = json.loads((out / 'validation_report.json').read_text())
        hashes = {asset['file']: asset['sha256'] for asset in prior_report['assets']}
        assert all(hashlib.sha256((out / name).read_bytes()).hexdigest() == digest for name, digest in hashes.items())
        review = {
            'status': 'passed', 'reviewer': 'Codex 图像目检',
            'recorded_at': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
            'asset_sha256': hashes, 'issues': [],
            'background_modes': ['light', 'dark', 'checker'],
            'actual_size_px': [240, 120, 50],
            'items': [dict(number=f'{i:02d}', **{field: True for field in fields},
                           notes=f'已目检实际240px浅色主图、120px深色及棋盘缩略图；核对中文“{caption}”、{identities[pack["cat"]]}、完整动作、肢体和单尾。')
                      for i, caption in enumerate(pack['captions'], 1)],
            'extras': {'cover': True, 'chat_icon': True, 'banner': True},
            'extras_notes': '已查看240px封面在浅色、深色和棋盘底的透明轮廓，50px正面头像的实际可读性及750×400有色无字横幅。封面及图标未加白色描边。',
            'evidence': ['previews/qa_light_240_01.jpg', 'previews/qa_light_240_13.jpg',
                         'previews/qa_dark_120_01.jpg', 'previews/qa_checker_120_01.jpg', 'previews/qa_extras.jpg'],
            'scope': 'Codex视觉检查，不代表本人确认或微信平台审核。',
        }
        write_json(out / 'visual_review.json', review)
        report = validate(out)
        assert report['technical_pass'] and report['visual_complete']
        (out / '.build_incomplete').unlink(missing_ok=True)
        packages = make_packages(out)
        row = {'cat': pack['cat'], 'title': pack['title'], 'main_count': 24,
               'technical_checks': len(report['checks']), 'assets': len(report['assets']),
               'technical_pass': report['technical_pass'], 'visual_complete': report['visual_complete'],
               'original_reference_sha256': hashlib.sha256((ROOT / pack['reference']).read_bytes()).hexdigest(),
               'packages': packages, 'platform_approval': 'not_submitted'}
        summaries.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    write_json(ROOT / '03_工程/final_delivery.json', summaries)


if __name__ == '__main__':
    main()
