#!/usr/bin/env python3
"""Retain actual tool originals and perform the installed chroma-key workflow."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import shutil
import subprocess
import sys
from zoneinfo import ZoneInfo
from PIL import Image

parser = argparse.ArgumentParser()
parser.add_argument('--record', required=True, type=Path)
args = parser.parse_args()
meta = json.loads(args.record.read_text())
version = Path(__file__).resolve().parent.parent
asset = meta['asset']
raw = version / '02_原画/生成原件' / (asset + '.png')
raw.parent.mkdir(exist_ok=True)
shutil.copy2(meta['original_tool_path'], raw)
with Image.open(raw) as im:
    meta['native_size'] = list(im.size)
    meta['native_mode'] = im.mode
meta['copied_raw_path'] = str(raw)
meta['raw_sha256'] = hashlib.sha256(raw.read_bytes()).hexdigest()
out = version / '02_原画' / (asset + '.png')
if asset == 'banner':
    shutil.copy2(raw, out)
    meta['postprocess'] = 'none; independent colored banner'
else:
    helper = Path('/Users/saymagic/.codex/skills/.system/imagegen/scripts/remove_chroma_key.py')
    command = [sys.executable, str(helper), '--input', str(raw), '--out', str(out),
               '--auto-key', 'border', '--soft-matte', '--transparent-threshold', '12',
               '--opaque-threshold', '220', '--despill']
    result = subprocess.run(command, text=True, capture_output=True)
    meta['postprocess'] = {'command': command, 'exit_code': result.returncode,
                           'stdout': result.stdout, 'stderr': result.stderr}
    if result.returncode:
        args.record.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
        raise SystemExit(result.returncode)
meta['processed_sha256'] = hashlib.sha256(out.read_bytes()).hexdigest()
meta['recorded_at'] = datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
args.record.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'asset': asset, 'native_size': meta['native_size'], 'raw_retained': True}, ensure_ascii=False))
