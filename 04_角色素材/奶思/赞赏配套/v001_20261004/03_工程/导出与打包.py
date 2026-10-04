"""Export size/encoding using sips/ffmpeg; inspect images with Pillow and package after actual review."""
import argparse, csv, hashlib, html, json, re, subprocess, zipfile
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parents[1]; out=root/'04_成品'; job=json.loads((root/'03_工程/job.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,value):p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def run(args):subprocess.run(args,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
parser=argparse.ArgumentParser();parser.add_argument('--package',action='store_true');args=parser.parse_args()
if not args.package:
    manifest=[];export=[]
    for item in job['items']:
        kind=item['kind'];w,h=item['size'];native=root/item['original'];full=root/f'03_工程/{kind}_全彩尺寸导出.png'
        run(['sips','-z',str(h),str(w),str(native),'--out',str(full)])
        base=job['label']+'_赞赏'+('引导图' if kind=='guide' else '致谢图')+f'_{w}x{h}'
        jpg=out/(base+'.jpg');limit=100000 if kind=='guide' else 200000
        for quality in [78,74,70,66,62,58,54,50]:
            run(['sips','-s','format','jpeg','-s','formatOptions',str(quality),str(full),'--out',str(jpg)])
            if jpg.stat().st_size<=limit:break
        png=out/(base+'.png')
        run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(full),'-vf','split[a][b];[a]palettegen=max_colors=256:reserve_transparent=0[p];[b][p]paletteuse=dither=none','-frames:v','1','-compression_level','9',str(png)])
        export.append({'kind':kind,'native_size':list(Image.open(native).size),'target_size':[w,h],'jpeg_quality':quality,'resize_tool':'macOS sips','png_encoding':'ffmpeg palettegen max_colors=256 reserve_transparent=0; paletteuse dither=none; compression_level=9','composition_changes':'none'})
        for file,fmt,cap in [(jpg,'JPEG',limit),(png,'PNG',500000)]:
            manifest.append({'file':file.name,'label':('赞赏引导图' if kind=='guide' else '赞赏致谢图')+' · '+('JPG' if fmt=='JPEG' else fmt),'characters':job['characters'],'caption':item['caption'],'spec':{'size':[w,h],'format':fmt,'alpha':False,'limit':cap,'limit_basis':'内部导出目标，非本次重新核对的官方上限'}})
    save(out/'manifest.json',manifest);save(out/'job.json',job)
    profile=json.loads((root/'03_工程/platform-profile.json').read_text());save(out/'platform-profile.json',profile)
    save(root/'03_工程/导出参数.json',{'image_tool':job['tool'],'model':job['model'],'quality':job['quality'],'font_name':job['font_name'],'font_file_distributed':False,'exports':export,'references':job['reference_override']})
    (out/'赞赏引导语.md').write_text('# '+job['title']+'的赞赏引导语\n\n'+'\n'.join(f'{i}. {text}' for i,text in enumerate(job['copy'],1))+'\n\n图中已使用：'+' / '.join(job['items'][0]['caption'])+'。\n致谢图已使用：'+' / '.join(job['items'][1]['caption'])+'。\n\n正式填写时以实际后台字数限制为准。\n')
    with (out/'captions.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['kind','width','height','line1','line2']);writer.writerows([i['kind'],*i['size'],*i['caption']] for i in job['items'])
    (out/'上传填写文案.md').write_text('# '+job['title']+'\n\n用于'+('、'.join(job['characters']))+'的赞赏配套图。\n\n引导语可选：\n\n'+'\n'.join('- '+x for x in job['copy'])+'\n\n图中文字、尺寸已在本地检查；本次未重新核实微信官方规格，没有进行微信投稿或审核。\n')
    cards=''
    for i in job['items']:
        rows=[x for x in manifest if x['caption']==i['caption']];jpg=next(x['file'] for x in rows if x['spec']['format']=='JPEG');png=next(x['file'] for x in rows if x['spec']['format']=='PNG')
        title='赞赏引导图' if i['kind']=='guide' else '赞赏致谢图';w,h=i['size']
        cards+=f'<article><h2>{title}</h2><img src="{jpg}" width="{w}" height="{h}" alt="{job["label"]}{title}"><p>{w}×{h}像素 · 奶油色背景</p><p><a href="{jpg}" download>JPG下载</a><a href="{png}" download>PNG下载</a></p></article>'
    page='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+job['title']+'</title><style>*{box-sizing:border-box}body{margin:0;background:#f7f4ec;color:#443a34;font:16px/1.7 system-ui,sans-serif}main{max-width:1160px;margin:auto;padding:24px 20px}h1{margin:10px 0}h2{font-size:22px}a{color:inherit;margin-right:12px;overflow-wrap:anywhere}.actions{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0}.actions a,article a{display:inline-block;border:1px solid #beb4a6;border-radius:10px;padding:8px 12px;text-decoration:none}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}article{min-width:0;padding:20px;background:#fffdf8;border:1px solid #e8e0d6;border-radius:20px}img{display:block;width:100%;height:auto}footer{font-size:14px;color:#75695f}@media(max-width:650px){.grid{grid-template-columns:1fr}main{padding:16px}article{padding:14px}}</style><main><a href="../../../../../表情包作品库.html">← 返回表情作品库</a><h1>'+html.escape(job['title'])+'</h1><p>'+('三只猫的喜欢，一起送给你。' if len(job['characters'])>1 else job['label']+'的小心意，软软送给你。')+'</p><p class="actions"><a href="submission_赞赏配套.zip" download>下载两图与引导语</a><a href="complete_materials.zip" download>完整制作备份</a></p><section class="grid">'+cards+'</section><h2>俏皮的赞赏引导语</h2><ol>'+''.join('<li>'+html.escape(x)+'</li>' for x in job['copy'])+'</ol><a href="赞赏引导语.md">查看文案文件</a><footer><p>按用户指定尺寸导出，角色形象、图中文字及压缩后画面需实际检查。本次未重新核实官方后台规格；微信投稿与审核未进行。</p></footer></main></html>'
    (out/'preview.html').write_text(page)
manifest=json.loads((out/'manifest.json').read_text());checks=[];assets=[]
for row in manifest:
    p=out/row['file'];spec=row['spec']
    with Image.open(p) as im:actual={'size':list(im.size),'format':im.format,'frames':getattr(im,'n_frames',1),'alpha':list(im.convert('RGBA').getchannel('A').getextrema())}
    for name,result in [('size',actual['size']==spec['size']),('format',actual['format']==spec['format']),('bytes',p.stat().st_size<=spec['limit']),('opaque',actual['alpha']==[255,255]),('single_frame',actual['frames']==1)]:checks.append({'file':row['file'],'check':name,'pass':result})
    assets.append({'file':row['file'],'sha256':sha(p),'bytes':p.stat().st_size,**actual})
report={'technical_pass':all(x['pass'] for x in checks),'checks':checks,'assets':assets,'official_rules_verified':False,'dimension_basis':'用户指定尺寸'};save(out/'validation_report.json',report)
save(root/'03_工程/原生文件与参考哈希.json',{'originals':[{'file':i['original'],'sha256':sha(root/i['original']),'size':list(Image.open(root/i['original']).size)} for i in job['items']],'references':[{'file':p.relative_to(root).as_posix(),'sha256':sha(p)} for p in sorted((root/'01_资料/参考').glob('*'))]})
if not report['technical_pass']:raise SystemExit('Technical checks failed')
if not args.package:
    print(json.dumps({'status':'technical_pass','assets':assets},ensure_ascii=False));raise SystemExit()
review=json.loads((out/'visual_review.json').read_text())
if review.get('status')!='passed' or review.get('asset_sha256')!={x['file']:x['sha256'] for x in assets}:raise SystemExit('Actual visual review required')
records=[]
for name,label in [('submission_赞赏配套.zip','两图与引导语'),('complete_materials.zip','完整制作备份')]:
    with zipfile.ZipFile(out/name,'w',zipfile.ZIP_DEFLATED) as z:
        if name.startswith('submission_'):
            for row in manifest:z.write(out/row['file'],row['file'])
            for textfile in ['赞赏引导语.md','manifest.json','captions.csv','上传填写文案.md']:z.write(out/textfile,textfile)
        else:
            for p in sorted(root.rglob('*')):
                if not p.is_file() or p.suffix=='.zip' or p.name in ('zip_validation.json','完成锁定.json'):continue
                rel=p.relative_to(out).as_posix() if p.is_relative_to(out) else p.relative_to(root).as_posix()
                if p.name=='preview.html':
                    text=p.read_text().replace('../../../../../表情包作品库.html','#');text=re.sub(r'<a href="[^\"]+\.zip"[^>]*>.*?</a>','',text);z.writestr(rel,text)
                else:z.write(p,rel)
    with zipfile.ZipFile(out/name) as z:
        names=z.namelist();ok=z.testzip() is None and len(names)==len(set(names))
        ok=ok and {row['file']:hashlib.sha256(z.read(row['file'])).hexdigest() for row in manifest}=={x['file']:x['sha256'] for x in assets}
        for n in names:
            if n.endswith('.html'):
                for link in re.findall(r'(?:src|href)="([^\"]+)"',z.read(n).decode()):
                    if not link.startswith(('http:','https:','#','data:')) and (Path(n).parent/link).as_posix() not in names:raise SystemExit('ZIP missing link: '+link)
    if not ok:raise SystemExit('ZIP validation failed')
    records.append({'file':name,'label':label,'sha256':sha(out/name),'bytes':(out/name).stat().st_size,'content_verified':True,'files':len(names)})
save(out/'zip_validation.json',records);print(json.dumps({'status':'packaged','packages':records},ensure_ascii=False))
