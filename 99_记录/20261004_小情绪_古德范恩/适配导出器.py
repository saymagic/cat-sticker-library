#!/usr/bin/env python3
"""Copy and adapt the library exporter for honest 8–24 item jobs."""
from pathlib import Path
import hashlib, json, shutil

ROOT=Path(__file__).resolve().parents[2]
BATCH=Path(__file__).resolve().parent

def replace(source,old,new):
    if old not in source: raise ValueError('Missing adaptation anchor: '+old)
    return source.replace(old,new)

build=(ROOT/'03_工程/build_pack.py').read_text()
build=replace(build,'Build one 24-item static pack','Build one 8-to-24-item static pack')
build=replace(build,'if len(items) != 24:\n        raise ValueError(f"每个 job 必须恰好24条 items，当前为{len(items)}")','if not 8 <= len(items) <= 24 or job.get("count", len(items)) != len(items):\n        raise ValueError(f"每个 job 必须为8至24条且count一致，当前为{len(items)}")')
build=replace(build,'if len(set(meanings)) != 24:', 'if len(set(meanings)) != len(items):')
build=replace(build,'24条 meaning 须唯一','全部 meaning 须唯一')
build=replace(build,'def previews(root, items, title, font_path):','def previews(root, items, title, font_path, profile_date):')
build=replace(build,'(1280, 1960)','(1280, 170 + ((len(items)+3)//4)*300)')
build=replace(build,'"24张静态表情 · 猫猫与文字白描边"','f"{len(items)}张静态表情 · 猫猫与文字白描边"')
build=replace(build,'24 张静态表情','__COUNT__ 张静态表情')
build=replace(build,'已核对2026年10月2日官方公开制作规范','已于__PROFILE_DATE__复核官方公开帮助文档的制作规范')
build=replace(build,'document.replace("__TITLE__", html.escape(title))','document.replace("__COUNT__", str(len(items))).replace("__PROFILE_DATE__", profile_date).replace("__TITLE__", html.escape(title))')
build=replace(build,'profile = json.loads(PROFILE.read_text(encoding="utf-8"))','profile = json.loads(PROFILE.read_text(encoding="utf-8"))\n    if profile.get("count") != len(job["items"]):\n        raise ValueError("平台快照count必须与本版实际items一致")')
build=replace(build,'art_layer = fit_art(art, (1024, 1024), (34, 238, 956, 754))','''art_layer = fit_art(art, (1024, 1024), (34, 238, 490, 754) if item.get("pie_chart") else (34, 238, 956, 754))
        if item.get("pie_chart"):
            # Native diagram: exactly 30% = 108 degrees, separate from generated cat art.
            diagram = Image.new("RGBA", (1024, 1024))
            d = ImageDraw.Draw(diagram)
            box = (606, 432, 946, 772)
            d.ellipse(box, fill="#E8DAD0", outline="#433535", width=8)
            d.pieslice(box, start=-90, end=18, fill="#81A9DC", outline="#433535", width=8)
            d.ellipse(box, outline="#433535", width=8)
            percent_font = ImageFont.truetype(font_path, 86)
            d.text((776, 832), "30%", font=percent_font, fill="#433535", anchor="mm", stroke_width=6, stroke_fill="#FFFFFF")
            save_png(diagram, output / "layers" / f"{number}_diagram.png")
            art_layer.alpha_composite(diagram)''')
build=replace(build,'previews(output, manifest, job["title"], font_path)','previews(output, manifest, job["title"], font_path, profile["basis_date"])')
build=replace(build,'\\n\\n24张静态表情；','\\n\\n{len(job["items"])}张静态表情；')
build=replace(build,"'已于2026年10月2日读取官方公开帮助中心的当前制作规范，导出体积采用更小目标。", "f'已于{profile[\"basis_date\"]}复核独立官方公开帮助文档的制作规范，导出体积采用更小目标。")
build=replace(build,'"count": 24,','"count": len(job["items"]),')

validate=(ROOT/'03_工程/validate_pack.py').read_text()
validate=replace(validate,'range(1, 25)', 'range(1, len(job["items"])+1)')
validate=replace(validate,'check(len(items) == 24, "exactly 24 stickers")','check(8 <= len(items) <= 24 and len(items) == profile.get("count") == job.get("count"), "actual 8-24 count matches job and profile")')
validate=replace(validate,'"numbering 01-24"','"continuous numbering matches actual count"')
validate=replace(validate,'len(set(meanings)) == 24','len(set(meanings)) == len(items)')
validate=replace(validate,'== 24, "24 distinct main files"','== len(items), "all main files distinct"')
validate=replace(validate,'尚未完成全部24张和配套素材的视觉复核','尚未完成全部主图和配套素材的视觉复核')
validate=replace(validate,'items = json.loads((root / "manifest.json").read_text(encoding="utf-8"))\n    archives = []','items = json.loads((root / "manifest.json").read_text(encoding="utf-8"))\n    job = json.loads((root / "job.json").read_text(encoding="utf-8"))\n    archives = []')
validate=replace(validate,'len(scoped) != 24','len(scoped) != len(items)')
validate=replace(validate,'for n in names) != 24','for n in names) != len(items)')

utils=(ROOT/'03_工程/pack_utils.py').read_text()
# Preserve rare green/blue eye pixels in the static compatibility GIF palette.
utils=replace(utils,'Image.Quantize.MEDIANCUT','Image.Quantize.MAXCOVERAGE')

entries=json.loads((ROOT/'作品目录.json').read_text())['entries']
data=(BATCH/'官方公开帮助文档.js').read_bytes()
if hashlib.sha256(data).hexdigest()!='9d16725d109eb65349369ceeda6212015d70af4f8121c34be92396bfe754cd78':
    raise ValueError('Public document changed: reparse before recording verified fields')
text=(ROOT/'00_官方调研/原始证据/官方帮助中心可见文本.txt').read_text()
print(text[text.index('1）动态表情须'):text.index('1）不超过 8 个汉字')])

for e in entries:
    if e['theme'] not in ('小情绪上辑','小情绪下辑'): continue
    v=ROOT/e['path']; eng=v/'03_工程'; export=eng/'导出器'
    if (v/'05_验收/完成锁定.json').is_file():
        print('Skip locked version: '+str(v))
        continue
    for name,content in [('build_pack.py',build),('validate_pack.py',validate),('pack_utils.py',utils)]:
        (export/name).write_text(content)
    profile=json.loads((ROOT/'03_工程/platform-profile.json').read_text())
    profile.update(name='wechat-public-guide-20261004-static14-conservative',basis_date='2026-10-04',official_rules_verified=True,count=14,
                   official_source='https://res.wxqcloud.qq.com.cn/t/wx_fed/base/sticker_platform/26052800/static/js/pages/guide/index.f84d77217115a9c8a0ed.js?1ba308c511fe82c68e48',
                   note='2026-10-04实际读取官方独立公开帮助文档，复核8至24张、240px静态主图、240px无白边封面、50px无白边聊天图标及750x400有色无字横幅。本版14张，导出上限低于公开规范。动态上传页面被浏览器安全策略阻止；未访问登录后投稿页，未微信投稿或审核。120px缩略图、240px图标与单帧GIF为兼容备用。')
    for p in [eng/'platform-profile.json',export/'platform-profile.json']:
        p.write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n')
    shutil.copy2(BATCH/'官方公开帮助文档.js',eng/'官方核对/官方公开帮助文档.js')
    shutil.copy2(ROOT/'00_官方调研/原始证据/官方帮助中心可见文本.txt',eng/'官方核对/官方帮助文档可见文本.txt')
    evidence={'checked_date':'2026-10-04','access_channel':'independent official public documentation CDN; HTTP 200','official_document_url':profile['official_source'],'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'verified_fields':['static240','count8-24','cover240_no_white_contour','chat_icon50_no_white_contour','banner750x400_color_no_text'],'logged_in_upload_page_verified':False,'guide_browser_page':'blocked_by_browser_security_policy','text_derivation':'当前下载的官方脚本SHA256与原始可见文本来源脚本相同；本次实际复读相关字段，未仅修改旧快照日期','export_count':14}
    (eng/'官方核对/本次核对记录.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    (export/'适配说明.md').write_text('# 8至24张静态导出器\n\n源自本库03_工程的首批24张适配器，本版改为实际items、job.count与profile.count一致且8至24之间；连续编号、独立主图、ZIP与视觉项数量均取实际值，预览高度和文案按实际数量。没有复制图片来凑数。封面/图标不加白边。静态GIF使用MAXCOVERAGE保留眼色。三分冷漠另存原生diagram图层，108度/360度=30%，不改动生成的猫图。原画及中文分层保存，全部经过实际素材及ZIP检查。\n')
    compile(build,str(export/'build_pack.py'),'exec');compile(validate,str(export/'validate_pack.py'),'exec');compile(utils,str(export/'pack_utils.py'),'exec')
print('Prepared 4 count-aware exporters and dated official-document evidence.')
