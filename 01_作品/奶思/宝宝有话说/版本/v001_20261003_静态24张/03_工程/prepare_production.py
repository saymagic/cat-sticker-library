"""Archive production inputs and transcribe the actual authored visual decisions.
No visual result is inferred from pixels or program exit status.
"""
from pathlib import Path
import json,shutil,hashlib
from datetime import datetime
from zoneinfo import ZoneInfo
V=Path(__file__).resolve().parent.parent
O=V/'04_成品';P=O/'production';P.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for folder in ['01_资料','03_工程']:
 target=P/folder;target.mkdir(exist_ok=True)
 for p in (V/folder).rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts and p.name not in ['作品信息.json']:
   dest=target/p.relative_to(V/folder);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
shutil.copytree(V/'02_原画/生成原件',P/'原始生成文件',dirs_exist_ok=True)
shutil.copytree(V/'05_验收/视觉证据',P/'视觉证据',dirs_exist_ok=True)
job=json.loads((O/'job.json').read_text())
rows='\n'.join(f"| {x['number']} | main/{x['number']}.png | {x['caption']} | {x['meaning']} |" for x in job['items'])
(O/'上传填写文案.md').write_text(f'''# {job['title']}上传填写文案\n\n专辑名称：{job['title']}\n\n介绍：{job['description']}\n\n类型建议：卡通；内容建议：猫咪、宝宝、日常、撒娇、小情绪（以后台实际选项为准）。\n\n版权信息：由本人使用真实设计师或工作室名称填写，不编造，公开规范最多10个汉字。艺术家名称：使用真实账号资料，本任务未自动设置。\n\n制作说明：依据作品库本版奶思卡通基准，使用image_gen工具辅助独立绘制24张无字原画；中文由确定性排版添加。工具未披露模型名称或质量参数。参考的权利关系按真实来源声明；本地技术与目检通过不代替本人资料、授权和平台审核。字体为站酷快乐体，SIL OFL 1.1许可，ZIP不附字体二进制。\n\n| 编号 | 主图文件 | 中文文案 | 唯一含义词 |\n| --- | --- | --- | --- |\n{rows}\n\n优先使用submission_PNG.zip；submission_GIF.zip是同内容单帧静态兼容包，不是动画。240px封面、50px聊天图标无白描边，750x400横幅有色无字；120px缩略图和240px图标仅作兼容备用。微信状态：未投稿。\n''',encoding='utf-8')
for p in [V/'03_工程/导出器/build_pack.py',O/'scripts/build_pack.py',P/'03_工程/导出器/build_pack.py']:
 p.write_text(p.read_text().replace('已于2026年10月2日','已于2026年10月3日'),encoding='utf-8')
p=O/'delivery_notes.md';p.write_text(p.read_text().replace('已于2026年10月2日','已于2026年10月3日')+'\n当日规格由默认TLS读取官方公开HTML及静态JS后实际核对。官方帮助中心浏览器访问被站点安全策略阻止，没有绕过；登录投稿页未核对。\n',encoding='utf-8')
report=json.loads((O/'validation_report.json').read_text())
review=json.loads((V/'05_验收/人工逐张目检记录.json').read_text())
review['recorded_at']=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
review['asset_sha256']={x['file']:x['sha256'] for x in report['assets']}
review['evidence']=[{'file':'production/视觉证据/'+p.name,'sha256':sha(p),'size_px':None,'note':'实际1:1检查图，已通过view_image实际查看'} for p in sorted((P/'视觉证据').glob('*.png'))]
review['manual_decision_source']={'file':'05_验收/人工逐张目检记录.json','sha256':sha(V/'05_验收/人工逐张目检记录.json')}
dump(O/'visual_review.json',review)
shutil.copyfile(V/'05_验收/人工逐张目检记录.json',P/'人工逐张目检记录.json')
dump(V/'05_验收/原画问题复检.json',{'reviewer':'Codex实际图像目检','reviewed_at':review['recorded_at'],'resolved':[{'number':'02','selected_revision':'r3','result':'PASS','finding':'重新绘制眉上找人姿态，最终Alpha通过，三底色240/120px无光晕','failed_originals_kept':True},{'number':'21','selected_revision':'r2','result':'PASS','finding':'独立重画侧躺扶额，最终Alpha通过且无光晕','failed_originals_kept':True},{'number':'24','selected_revision':'r2','result':'PASS','finding':'独立方形原画趴垫，最终Alpha通过且无光晕','failed_originals_kept':True}]})
for name in ['原画首轮技术检查.json','原画最终技术检查.json','原画问题记录.json','原画问题复检.json']:
 shutil.copyfile(V/'05_验收'/name,P/name)
(P/'重现说明.md').write_text('''# 重现说明\n\n所有选定原画在sources，原始工具返回PNG（含真实失败版本）在production/原始生成文件；提示词、实际工具返回提示和来源哈希在production/03_工程。\n\n使用Pillow、numpy与可用中文字体，解压后运行scripts/build_pack.py --job job.json --out 新空目录 --no-package。需要站酷快乐体时由字体来源.json里的官方URL下载，核对SHA256；字体二进制不在ZIP。生成和排版参数在job、manifest、provenance。重导会生成pending目检，必须实际重看导出的最终素材再打包，不复用旧通过结论。\n\n模板默认PNG240、缩略图120、封面240、聊天图标50、横幅750x400；GIF只有一帧。完整备份不包含其他ZIP，解压后的preview不含ZIP下载链接，避免悬空引用。\n''',encoding='utf-8')
print(json.dumps({'production_files':sum(p.is_file() for p in P.rglob('*')),'visual_items_authored':len(review['items']),'visual_asset_hashes':len(review['asset_sha256'])},ensure_ascii=False))
