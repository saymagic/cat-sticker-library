from pathlib import Path
import html
import json
import shutil
import zipfile
import hashlib
import re

ROOT=Path(__file__).resolve().parents[1]

def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    packs=json.loads((ROOT/'03_工程/packs.json').read_text())
    sections=[];tabs=[];registry=[];packages=[]
    upload_dir=ROOT/'02_上传包';upload_dir.mkdir(exist_ok=True)
    for p in packs:
        version=Path(p['version_dir']);out=version/'04_成品'
        rel=out.relative_to(ROOT).as_posix()
        tabs.append(f'<button class="cat-tab" data-cat="{p["id"]}" aria-pressed="false">{p["cat"]}<span>24 张</span></button>')
        cards=''.join(f'<article class="sticker-card"><a class="artboard" href="{rel}/main_png/{i:02d}.png" target="_blank" aria-label="查看{p["cat"]}{html.escape(c)}主图"><img src="{rel}/main_png/{i:02d}.png" width="240" height="240" alt="{p["cat"]}：{html.escape(c)}"></a><div class="caption"><b>{i:02d}</b><span>{html.escape(c)}</span><a href="{rel}/main_png/{i:02d}.png" download>PNG</a></div></article>' for i,c in enumerate(p['captions'],1))
        stem=p['title']
        package_links=[]
        for encoding,source,label in [('PNG','submission_PNG.zip','上传PNG素材'),('GIF','submission_GIF.zip','单帧GIF备用'),('完整','complete_delivery.zip','完整制作备份')]:
            dst=upload_dir/f'{stem}_{encoding}_20261002.zip'
            if (out/source).is_file():
                shutil.copy2(out/source,dst)
                with zipfile.ZipFile(dst) as z:
                    assert z.testzip() is None
                    count=len(z.namelist())
                digest=hashlib.sha256(dst.read_bytes()).hexdigest()
                packages.append({'file':dst.relative_to(ROOT).as_posix(),'sha256':digest,'bytes':dst.stat().st_size,'files':count,'testzip':'PASS'})
            package_links.append(f'<a class="download" href="02_上传包/{dst.name}" download="{dst.name}">{label}<span>↓</span></a>')
        extras=f'<div class="extras-grid"><figure><div class="transparent"><img src="{rel}/extras/cover_240.png" width="240" height="240" alt="{p["cat"]}240px无白边封面"></div><figcaption>封面 · 240×240 · 无白边</figcaption></figure><figure><div class="icon-preview transparent"><img src="{rel}/extras/chat_icon_50.png" width="50" height="50" alt="{p["cat"]}50px无白边聊天图标"></div><figcaption>聊天图标 · 实际50×50 · 无白边</figcaption></figure><figure class="banner"><img src="{rel}/extras/banner_750x400.jpg" width="750" height="400" alt="{p["cat"]}有色无字横幅"><figcaption>详情页横幅 · 750×400 · 有色无字</figcaption></figure></div>'
        sections.append(f'<section class="pack" data-cat="{p["id"]}"><div class="pack-heading"><div><p class="eyebrow">{p["cat"]} / 静态专辑</p><h2>{p["title"]}</h2><p>{p["description"]}</p></div><a class="quiet-link" href="{rel}/上传填写文案.md">查看上传填写文案 ↗</a></div><div class="downloads">{"".join(package_links)}</div><div class="grid">{cards}</div><details><summary>封面、聊天图标和详情页横幅</summary>{extras}</details><p class="evidence"><a href="{rel}/validation_report.json">技术检查</a><a href="{rel}/visual_review.json">视觉复核</a><a href="{rel}/preview.html">单套预览</a></p></section>')
        report=json.loads((out/'validation_report.json').read_text()) if (out/'validation_report.json').exists() else {}
        registry.append({'character':p['cat'],'theme':p['title'],'version':'v001_20261002_静态24张','count':24,'type':'静态','path':version.relative_to(ROOT).as_posix(),'status':'本地成品' if report.get('technical_pass') and report.get('visual_complete') else '制作中','original_reference':p['reference'],'technical_checks':len(report.get('checks',[])),'platform_approval':'not_submitted'})
    document='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>三只猫的中文表情</title><style>
:root{--bg:#f6f2ed;--panel:#fffaf4;--ink:#49392f;--muted:#87766a;--line:#dfd3c7;--accent:#7a5039;--art:#faf7f2}*{box-sizing:border-box}body{margin:0;color:var(--ink);background:var(--bg);font:15px/1.6 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}a{color:inherit;text-decoration:none}button{font:inherit;cursor:pointer}header,main,footer{max-width:1320px;margin:auto;padding:28px 32px}.topline{display:flex;justify-content:space-between;align-items:center;font-size:12px;color:var(--muted);letter-spacing:.06em;border-bottom:1px solid var(--line);padding-bottom:16px}.hero{padding:34px 0 24px}.eyebrow{font-size:12px;letter-spacing:.12em;color:var(--muted);margin:0 0 8px}.hero h1{font-size:clamp(30px,5vw,52px);line-height:1.15;margin:0 0 18px;letter-spacing:-.02em}.hero p{color:var(--muted);max-width:760px}.facts{display:flex;gap:12px;flex-wrap:wrap}.facts span{font-size:12px;border:1px solid var(--line);padding:5px 12px;border-radius:30px}.controls{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;padding:18px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.tabs,.backgrounds{display:flex;gap:8px;flex-wrap:wrap}.tabs button,.backgrounds button{border:1px solid var(--line);border-radius:9px;padding:8px 14px;background:transparent;color:var(--ink)}.tabs button[aria-pressed=true],.backgrounds button[aria-pressed=true]{background:var(--ink);color:var(--bg);border-color:var(--ink)}.tabs span{opacity:.65;margin-left:9px;font-size:12px}.backgrounds{font-size:12px}.backgrounds button{padding:6px 10px}.pack{padding:12px 0 42px}.pack+.pack{border-top:1px solid var(--line)}.pack-heading{display:flex;justify-content:space-between;gap:20px;align-items:center}.pack-heading h2{font-size:29px;margin:0 0 8px}.pack-heading p:not(.eyebrow){margin:0;color:var(--muted)}.quiet-link{font-size:13px;text-decoration:underline;text-underline-offset:4px;white-space:nowrap}.downloads{display:flex;gap:10px;flex-wrap:wrap;margin:22px 0}.download{display:flex;justify-content:space-between;gap:28px;border:1px solid var(--line);border-radius:10px;background:var(--panel);padding:11px 16px;font-size:13px}.download:first-child{background:var(--accent);color:white;border-color:var(--accent)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(252px,1fr));gap:16px}.sticker-card{border:1px solid var(--line);border-radius:14px;background:var(--panel);overflow:hidden}.artboard{display:flex;justify-content:center;align-items:center;min-height:260px;background:var(--art)}.artboard img{width:240px;height:240px;object-fit:contain}.caption{display:flex;gap:10px;align-items:center;padding:11px 14px;border-top:1px solid var(--line);font-size:13px}.caption b{color:var(--muted);font-size:11px;font-weight:500}.caption a{margin-left:auto;font-size:11px;border-bottom:1px solid var(--line)}details{border:1px solid var(--line);border-radius:12px;margin-top:20px;padding:16px}summary{cursor:pointer;font-size:14px}.extras-grid{display:grid;grid-template-columns:240px 130px 1fr;align-items:center;gap:20px;margin-top:20px}figure{margin:0}figure img{display:block;max-width:100%;object-fit:contain}figcaption{font-size:11px;color:var(--muted);margin-top:10px}.banner img{width:100%;height:auto}.icon-preview{height:140px;display:grid;place-items:center}.evidence{display:flex;gap:20px;font-size:12px;color:var(--muted);margin-top:18px}.evidence a{text-decoration:underline}.dark{--art:#292c31}.checker .artboard,.checker .transparent{background:conic-gradient(#dad6d0 25%,#f4f0eb 0 50%,#dad6d0 0 75%,#f4f0eb 0) 0 0/20px 20px}footer{border-top:1px solid var(--line);font-size:12px;color:var(--muted)}footer a{text-decoration:underline}body[data-filter=naisi] .pack:not([data-cat=naisi]),body[data-filter=gude] .pack:not([data-cat=gude]),body[data-filter=fanen] .pack:not([data-cat=fanen]){display:none}
@media(max-width:600px){header,main,footer{padding:20px 16px}.topline{font-size:10px}.pack-heading{align-items:flex-start;flex-direction:column;gap:12px}.controls{align-items:flex-start}.downloads{gap:8px}.download{padding:10px 12px;gap:16px}.grid{grid-template-columns:1fr}.artboard{min-height:252px}.extras-grid{grid-template-columns:1fr;justify-items:center}.banner{width:100%}.pack-heading h2{font-size:25px}.evidence{gap:14px;flex-wrap:wrap}}
</style></head><body data-filter="all"><header><div class="topline"><span>奶思 · 古德 · 范恩</span><span>2026.10.02 / 中文静态表情</span></div><div class="hero"><p class="eyebrow">每一句回应，都有一只猫</p><h1>三只猫的中文日常</h1><p>沿用原始卡通形象和手绘贴纸框架：中文短句在上，猫咪动作在下。保留各自的毛色、眼睛和神态，用72个独立画面，接住聊天里的小情绪。</p><div class="facts"><span>3 套 × 24 张</span><span>240px 透明主图</span><span>封面 · 图标 · 横幅齐备</span><span>附中文填写表</span></div></div><nav class="controls" aria-label="预览控制"><div class="tabs"><button data-cat="all" aria-pressed="true">全部<span>72 张</span></button>__TABS__</div><div class="backgrounds"><button data-bg="light" aria-pressed="true">浅色</button><button data-bg="dark" aria-pressed="false">深色</button><button data-bg="checker" aria-pressed="false">透明棋盘</button></div></nav></header><main>__SECTIONS__</main><footer><p><a href="00_官方调研/微信表情制作与投稿调研.md">查看官方制作原理与材料调研</a> · <a href="00_官方调研/验收说明.md">查看交付检查与上传说明</a></p><p>已核对2026年10月2日官方公开制作规范。图片完成本地技术检查和Codex视觉复核；本人艺术家资料、真实版权信息、平台投稿与审核尚未完成。GIF备用包均为单帧静态图。120px缩略图和240px聊天图标为兼容备用。</p></footer><script>
document.querySelectorAll('.tabs button').forEach(button=>button.addEventListener('click',()=>{document.body.dataset.filter=button.dataset.cat;document.querySelectorAll('.tabs button').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));}));document.querySelectorAll('.backgrounds button').forEach(button=>button.addEventListener('click',()=>{document.body.className=button.dataset.bg==='light'?'':button.dataset.bg;document.querySelectorAll('.backgrounds button').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));}));
</script></body></html>'''
    (ROOT/'三猫表情包预览.html').write_text(document.replace('__TABS__',''.join(tabs)).replace('__SECTIONS__',''.join(sections)),encoding='utf-8')
    write_json(ROOT/'作品目录.json',{'date':'2026-10-02','characters':['奶思','古德','范恩'],'works':registry})
    write_json(upload_dir/'ZIP校验.json',packages)
    (upload_dir/'SHA256SUMS.txt').write_text(''.join(f'{x["sha256"]}  {Path(x["file"]).name}\n' for x in packages),encoding='utf-8')
    markup=(ROOT/'三猫表情包预览.html').read_text()
    links=re.findall(r'(?:src|href)="([^"]+)"',markup)
    missing=[p for p in links if not p.startswith(('http','#','data:')) and not (ROOT/p).is_file()]
    write_json(ROOT/'03_工程/preview_links.json',{'checked':len(links),'missing':missing,'status':'PASS' if not missing else 'PENDING'})
    print(json.dumps({'packages':len(packages),'links_checked':len(links),'missing':len(missing),'page':str(ROOT/'三猫表情包预览.html')},ensure_ascii=False))

if __name__=='__main__':main()
