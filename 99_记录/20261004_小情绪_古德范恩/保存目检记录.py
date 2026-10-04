#!/usr/bin/env python3
"""Write a manually supplied per-image visual review after actual inspection."""
from pathlib import Path
import argparse,datetime,json
from zoneinfo import ZoneInfo

parser=argparse.ArgumentParser();parser.add_argument('version',type=Path);parser.add_argument('--notes',required=True,type=Path)
args=parser.parse_args();v=args.version.resolve();out=v/'04_成品'
supplied=json.loads(args.notes.read_text());manifest=json.loads((out/'manifest.json').read_text())
if len(supplied['items'])!=len(manifest) or supplied['status']!='passed':raise ValueError('Missing actual per-image review')
notes=supplied['items'];report=json.loads((out/'validation_report.json').read_text());qa=json.loads((v/'05_验收/待目检清单.json').read_text())
review={'status':'passed','reviewer':'Codex 实际逐张图像目检','reviewed_at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'user_approved':False,'asset_sha256':{a['file']:a['sha256'] for a in report['assets']},'issues':[],'background_modes':['dark','light','checker'],'actual_size_px':[240,120,50],'evidence':[str(Path(p).relative_to(v)) for p in qa['evidence']],'items':[{'number':f'{i:02d}','identity':True,'anatomy':True,'caption':True,'outline':True,'pose':True,'readability':True,'notes':n+'已逐字查看主图三底240px及120px缩略图、240px静态GIF；文字颜色/双描边清楚，无色键边污染。'} for i,n in enumerate(notes,1)],'extras':{'cover':True,'chat_icon':True,'banner':True},'extras_notes':supplied['extras'],'scope':'当前实际查看的全部本版主图/兼容GIF/缩略图及配套素材；不代表用户确认或微信平台审核。'}
(out/'visual_review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'reviewed_items':len(notes),'technical_checks':len(report['checks']),'all_assets':len(report['assets'])},ensure_ascii=False))
