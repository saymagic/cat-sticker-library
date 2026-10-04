"""Read-only asset checks and archive creation; no image generation or editing."""
import hashlib, json, re, zipfile
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parents[1]
out=root/'04_成品'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v): p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
manifest=json.loads((out/'manifest.json').read_text())
checks=[];assets=[]
for row in manifest:
    p=out/row['file'];spec=row['spec']
    with Image.open(p) as im:
        actual=dict(size=list(im.size),format=im.format,frames=getattr(im,'n_frames',1),alpha=list(im.convert('RGBA').getchannel('A').getextrema()))
    for name,result in [('size',actual['size']==spec['size']),('format',actual['format']==spec['format']),('bytes',p.stat().st_size<=spec['limit']),('opaque',actual['alpha']==[255,255]),('single_frame',actual['frames']==1)]:
        checks.append(dict(file=row['file'],check=name,pass_=result))
    assets.append(dict(file=row['file'],sha256=sha(p),bytes=p.stat().st_size,**actual))
checks=[{('pass' if k=='pass_' else k):v for k,v in c.items()} for c in checks]
report=dict(technical_pass=all(c['pass'] for c in checks),checks=checks,assets=assets,dimension_basis='用户指定尺寸',official_rules_verified=False)
dump(out/'validation_report.json',report)
native=[dict(file=p.relative_to(root).as_posix(),sha256=sha(p),bytes=p.stat().st_size,size=list(Image.open(p).size)) for p in (root/'02_原画').glob('*.png')]
dump(root/'03_工程/原生文件与参考哈希.json',dict(originals=native,reference_sha256=sha(root/'01_资料/参考/卡通基准.png')))
if not report['technical_pass']: raise SystemExit('Technical checks failed')
review=json.loads((out/'visual_review.json').read_text()) if (out/'visual_review.json').exists() else {}
if review.get('status')!='passed' or review.get('asset_sha256')!={x['file']:x['sha256'] for x in assets}:
    print(json.dumps(dict(technical_pass=report['technical_pass'],checks=len(checks),assets=assets),ensure_ascii=False))
    raise SystemExit('Images checked; actual visual review is required before packaging')
records=[]
for name,label in [('submission_赞赏配套.zip','两图与引导语'),('complete_materials.zip','完整制作备份')]:
    with zipfile.ZipFile(out/name,'w',zipfile.ZIP_DEFLATED) as z:
        if name.startswith('submission_'):
            for row in manifest:z.write(out/row['file'],row['file'])
            z.write(out/'赞赏引导语.md','赞赏引导语.md')
            z.write(out/'manifest.json','manifest.json')
        else:
            for p in sorted(root.rglob('*')):
                if not p.is_file() or p.suffix=='.zip' or p.name in ('zip_validation.json','完成锁定.json'):continue
                rel=p.relative_to(out).as_posix() if p.is_relative_to(out) else p.relative_to(root).as_posix()
                if p.name=='preview.html':
                    text=p.read_text().replace('../../../../../表情包作品库.html','#')
                    text=re.sub(r'<a href="[^\"]+\.zip"[^>]*>.*?</a>','',text)
                    z.writestr(rel,text)
                else:z.write(p,rel)
    with zipfile.ZipFile(out/name) as z:
        names=z.namelist()
        ok=z.testzip() is None and len(names)==len(set(names))
        image_hashes={row['file']:hashlib.sha256(z.read(row['file'])).hexdigest() for row in manifest}
        ok=ok and image_hashes=={x['file']:x['sha256'] for x in assets}
        for n in names:
            if n.endswith('.html'):
                for link in re.findall(r'(?:src|href)="([^\"]+)"',z.read(n).decode()):
                    if not link.startswith(('http:','https:','#','data:')) and (Path(n).parent/link).as_posix() not in names:
                        raise SystemExit('ZIP preview link missing: '+link)
    if not ok:raise SystemExit('ZIP validation failed')
    records.append(dict(file=name,label=label,sha256=sha(out/name),bytes=(out/name).stat().st_size,content_verified=True,files=len(names)))
dump(out/'zip_validation.json',records)
print(json.dumps(dict(technical_checks=len(checks),assets=len(assets),packages=records),ensure_ascii=False))
