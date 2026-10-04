from pathlib import Path
import hashlib,json,re
from datetime import datetime
from zoneinfo import ZoneInfo
V=Path(__file__).resolve().parent.parent
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
js=V/'03_工程/官方公开制作规范-20261003.js'
s=js.read_text()
start=s.index('表情制作规范') if '表情制作规范' in s else s.index('8～24')-3000
# Preserve read-only static text actually inspected, rather than claiming live browser rendering.
section=s[s.index('8～24')-600:s.index('8～24')+17000]
visible='\n'.join(json.loads('"'+x+'"') for x in re.findall(r'e\._v\("((?:[^"\\]|\\.)*)"\)',section))
(V/'03_工程/官方规范-当日读取文本.txt').write_text(visible,encoding='utf-8')
checks={'main_count':'8～24','main_size':'240*240','static_formats':'静态表情：PNG、JPG或GIF','main_file_limit':'不大于500KB','banner_size':'750*400','cover_size':'240*240','chat_icon_size':'50*50','icon_file_limit':'不大于100KB','cover_no_white_outline':'图片中形象不应有白色描边','banner_no_text':'图片中避免出现任何文字信息','banner_opaque':'避免使用透明背景'}
found={k:{'expected_text':v,'present_in_live_official_bundle':v in s} for k,v in checks.items()}
now=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
profile=json.loads((V/'03_工程/platform-profile.json').read_text())
profile.update(name='wechat-official-20261003-static-conservative',basis_date='2026-10-03',official_rules_verified=True,note='2026-10-03经默认TLS重新读取官方帮助中心HTML及其公开静态JS，实际检查制作规范文字与字段；主图240px、8至24张、封面240px、聊天图标50px、横幅750x400有当日证据。导出采用更小体积上限；120px缩略图、240px聊天图标和单帧GIF明确为兼容备用。官方帮助中心浏览器访问被站点安全策略阻止，未绕过；无登录上传页或微信审核验证。')
profile['verification']={'checked_at':now,'method':'read-only official public HTML and static JS over verified TLS','browser_status':'BLOCKED_SITE_SAFETY_POLICY','logged_in_upload_page_verified':False,'verified_fields':['main_count','main_size','main_formats','main_max_500KB','cover_transparency','chat_icon_transparency','cover_size','cover_no_white_outline','chat_icon_size','chat_icon_max_100KB','banner_size','banner_opaque','banner_no_text'],'unverified_fields':['logged-in upload form','current thumbnail requirement','optional appreciation','artist identity','copyright authorization','WeChat approval'],'evidence_files':[{'file':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in [V/'03_工程/官方帮助中心-20261003.html',js,V/'03_工程/官方规范-当日读取文本.txt']],'source_urls':['https://sticker.weixin.qq.com/cgi-bin/mmemoticon-bin/readtemplate?t=guide/index.html#/makingSpecifications','https://res.wxqcloud.qq.com.cn/t/wx_fed/base/sticker_platform/26052800/static/js/pages/guide/index.f84d77217115a9c8a0ed.js?1ba308c511fe82c68e48']}
dump(V/'03_工程/platform-profile.json',profile)
dump(V/'03_工程/导出器/platform-profile.json',profile)
dump(V/'03_工程/规格字段核对.json',{'checked_at':now,'fields':found,'result':'PASS_PUBLIC_STATIC_SPEC','browser':'BLOCKED','logged_in_form':'NOT_RUN'})
font=Path('/Users/saymagic/Library/Fonts/ZCOOLKuaiLe-Regular.ttf')
dump(V/'03_工程/字体来源.json',{'font_name':'ZCOOL KuaiLe / 站酷快乐体','path':str(font),'sha256':sha(font),'license':'SIL Open Font License 1.1','font_source':'https://raw.githubusercontent.com/google/fonts/main/ofl/zcoolkuaile/ZCOOLKuaiLe-Regular.ttf','license_source':'https://github.com/googlefonts/zcool-kuaile/blob/main/OFL.txt','verified_at':now,'font_binary_distributed_in_ZIP':False})
dump(V/'05_验收/原画问题记录.json',{'reviewer':'Codex实际图像查看','issues':[{'number':'02','stage':'original generation','status':'OPEN','finding':'生成版含浅褐光晕且Alpha最大254，须用实际图像工具重新生成干净透明原画'}]})
print(json.dumps(found,ensure_ascii=False))
