#!/usr/bin/env python3
"""Preflight originals, export actual job, retain evidence and render review sheets.

This writes no visual verdict. Review sheets must be viewed before review JSON.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
import numpy as np

def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

parser=argparse.ArgumentParser();parser.add_argument('version',type=Path)
args=parser.parse_args();v=args.version.resolve();eng=v/'03_工程';out=v/'04_成品';qa=v/'05_验收/目检底图'
job=json.loads((eng/'job.json').read_text());qa.mkdir(exist_ok=True)

checks=[]
for asset in [x['number'] for x in job['items']]+list(job['extras']):
    p=v/'02_原画'/f'{asset}.png';record=eng/'生成记录'/f'{asset}.json'
    meta=json.loads(record.read_text());raw=Path(meta['copied_raw_path'])
    with Image.open(raw) as im:native=list(im.size)
    with Image.open(p) as im:
        a=np.asarray(im.convert('RGBA'))[...,3]
        minsize=min(im.size); alpha=im.mode=='RGBA' and (int(a.min()),int(a.max()))==(0,255)
        corners=[int(a[y,x]) for x,y in [(0,0),(im.width-1,0),(0,im.height-1),(im.width-1,im.height-1)]]
        source_ok=p.is_file() and sha(raw)==meta['raw_sha256'] and sha(p)==meta['processed_sha256'] and list(im.size)==native
        transparent_ok=asset=='banner' or (alpha and corners==[0,0,0,0] and .015 < float((a>=8).mean()) < .93)
        minimum_ok=(im.width>=750 and im.height>=400) if asset=='banner' else minsize>=1024
        checks.append({'asset':asset,'pass':source_ok and minimum_ok and transparent_ok,'native_size':native,'processed_size':list(im.size),'alpha':alpha,'corners':corners,'coverage':float((a>=8).mean()),'sha256':sha(p),'tool_receipt':str(record)})
dump(eng/'原画技术检查.json',checks)
if not all(c['pass'] for c in checks):
    print(json.dumps([c for c in checks if not c['pass']],ensure_ascii=False));raise SystemExit(1)

# The library creates a zero-byte Git placeholder, not a production output.
placeholder=out/'.gitkeep'
if placeholder.is_file() and placeholder.stat().st_size==0:
    placeholder.unlink()
r=subprocess.run([sys.executable,str(eng/'导出器/build_pack.py'),'--job',str(eng/'job.json'),'--out',str(out),'--no-package'],capture_output=True,text=True)
print(r.stdout);print(r.stderr,file=sys.stderr)
if r.returncode:raise SystemExit(r.returncode)

# Archive only nonsensitive production evidence; do not ship font binaries.
production=out/'production';production.mkdir()
shutil.copytree(v/'01_资料',production/'资料',ignore=shutil.ignore_patterns('作品信息.json'))
for name in ['提示词','生成记录','官方核对']:
    shutil.copytree(eng/name,production/name)
for name in ['本版制作计划.md','原画技术检查.json','接收与透明处理.py']:
    shutil.copy2(eng/name,production/name)
shutil.copytree(v/'02_原画/生成原件',production/'生成原件')
shutil.copy2(eng/'字体/OFL.txt',production/'字体许可.txt')
shutil.copy2(eng/'字体/字体说明.md',production/'字体说明.md')
shutil.copy2(eng/'上传填写文案.md',out/'上传填写文案.md')
(production/'重现说明.md').write_text('# 重现本版\n\n本版14张静态；sources保存独立透明猫图，production/生成原件保存实际工具原生色键底图，layers保留排字及精确扇形图，masters为1024px母版。安装Python/Pillow/numpy及具有SIL OFL许可的ZCOOL KuaiLe字体后，运行scripts/build_pack.py --job job.json --out 一个新空目录 --font 实际字体路径 --no-package，再进行技术和真实目检。完整备份不含字体二进制或平台身份资料。扇形108度=30%，生成的猫图未被程序重画。\n')

font=ImageFont.truetype(str(eng/'字体/ZCOOLKuaiLe-Regular.ttf'),20)
manifest=json.loads((out/'manifest.json').read_text())
def tile(size,mode):
    color={'light':(248,247,244),'dark':(37,39,43),'checker':(245,245,245)}[mode]
    im=Image.new('RGB',size,color)
    if mode=='checker':
        d=ImageDraw.Draw(im)
        for y in range(0,size[1],12):
            for x in range(0,size[0],12):
                if (x//12+y//12)%2:d.rectangle((x,y,x+11,y+11),fill=(215,215,215))
    return im

evidence=[]
for start in [0,7]:
    subset=manifest[start:start+7];sheet=Image.new('RGB',(840,64+len(subset)*272),(239,237,232));d=ImageDraw.Draw(sheet)
    for col,mode in enumerate(['light','dark','checker']):d.text((col*280+16,12),f'{mode} · 240px',font=font,fill=(50,46,40))
    for row,item in enumerate(subset):
        im=Image.open(out/item['main_png']).convert('RGBA')
        for col,mode in enumerate(['light','dark','checker']):
            bg=tile((240,240),mode);bg.paste(im,(0,0),im);x=col*280+20;y=60+row*272
            sheet.paste(bg,(x,y));d.text((x,y+242),f'{item["number"]} {item["caption"]}',font=font,fill=(50,46,40))
    p=qa/f'主图240三底_{start+1:02d}-{start+len(subset):02d}.png';sheet.save(p);evidence.append(str(p))

# One native 120px thumbnail column and native 240px GIF column per item.
for start in [0,7]:
    subset=manifest[start:start+7];sheet=Image.new('RGB',(560,50+len(subset)*266),(248,247,244));d=ImageDraw.Draw(sheet)
    d.text((14,8),'120px缩略图 / 240px单帧GIF',font=font,fill=(50,46,40))
    for row,item in enumerate(subset):
        y=50+row*266
        for key,x,mode in [('thumbnail',24,'dark'),('main_gif',268,'checker')]:
            im=Image.open(out/item[key]).convert('RGBA');bg=tile(im.size,mode);bg.paste(im,(0,0),im);sheet.paste(bg,(x,y))
        d.text((20,y+240),item['number']+' '+item['caption'],font=font,fill=(50,46,40))
    p=qa/f'缩略及GIF_{start+1:02d}-{start+len(subset):02d}.png';sheet.save(p);evidence.append(str(p))

sheet=Image.new('RGB',(840,900),(240,238,233));d=ImageDraw.Draw(sheet)
for row,(name,size) in enumerate([('cover_240.png',240),('chat_icon_50.png',50)]):
    im=Image.open(out/'extras'/name).convert('RGBA')
    for col,mode in enumerate(['light','dark','checker']):
        bg=tile((240,240),mode);bg.paste(im,((240-size)//2,(240-size)//2),im);sheet.paste(bg,(20+col*280,40+row*290))
        d.text((20+col*280,14+row*290),f'{name} {mode}',font=font,fill=(50,46,40))
banner=Image.open(out/'extras/banner_750x400.jpg');sheet.paste(banner,(45,620)) if banner.height+620<=900 else None
# Keep banner at its native size in a separate evidence image.
p=qa/'配套三底.png';sheet.crop((0,0,840,604)).save(p);evidence.append(str(p))
p=qa/'横幅实际750x400.jpg';shutil.copy2(out/'extras/banner_750x400.jpg',p);evidence.append(str(p))
dump(v/'05_验收/待目检清单.json',{'status':'pending','items':[x['number'] for x in manifest],'backgrounds':['light','dark','checker'],'actual_sizes':[240,120,50],'evidence':evidence,'note':'底图生成仅供真实目检；未自动填写视觉通过。'})
print(json.dumps({'version':str(v),'count':len(manifest),'original_checks':len(checks),'qa_sheets':evidence},ensure_ascii=False))
