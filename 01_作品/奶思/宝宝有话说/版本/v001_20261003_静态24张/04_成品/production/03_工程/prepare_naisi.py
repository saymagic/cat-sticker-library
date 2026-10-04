from pathlib import Path
import csv, hashlib, json, shutil

V=Path(__file__).resolve().parent.parent
ROOT=V.parents[4]
def dump(p,v): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
entry=next(x for x in json.loads((ROOT/'作品目录.json').read_text())['entries'] if x['id']=='pack-b8d226d1bc49')
ref=V/'01_资料/参考/卡通基准.png'
registry={'schema_version':1,'characters':[{'id':'naisi','name':'奶思','aliases':['奶思猫','乃斯','灰虎斑猫'],'identity':['灰黑虎斑短毛，金棕眼，奶油口鼻与粉鼻','圆润幼猫脸，耳内粉色，细软手绘毛纹，紧凑幼猫身形，以锁定卡通图为准'],'avoid':['禁止变成棕虎斑绿眼古德或蓝眼长毛范恩','不复制参考英文，不从总览裁切原画','四肢合理且仅一条尾巴，不套用内置照片'],'reference_basis':'本库锁定卡通基准，已由Codex实际查看原图','references':[{'path':str(ref),'kind':'locked_cartoon_master','role':'本版角色身份与画风基准','sha256':sha(ref)}]}]}
dump(V/'01_资料/角色快照.json',registry)
captions=json.loads((V/'01_资料/input.json').read_text())['captions']
rows=[
('早安','开心','#F2C454','坐直举一只前爪招手，后爪着地，尾巴侧弯，小太阳','sits upright, one rounded front paw lifted in a cheerful morning wave, other front paw relaxed, two hind paws planted, one striped tail curling aside, a small golden sunrise disk'),
('寻人','期待','#81A9DC','站立扶着门框探头找人，一条尾巴在身后轻弯','peeks around a small pale wooden doorframe, three-quarter view, curious searching gold-brown eyes, one front paw rests on the frame, other paws plausibly occluded, single striped tail curves behind'),
('到啦','雀跃','#EA92AD','小跑前冲，一爪举起打招呼，尾巴翘起，背小挎包','trots toward the viewer in three-quarter view with a tiny pale pink crossbody bag, lifts one front paw to greet, remaining legs clear in a light running step, one upright striped tail, delighted open-mouth smile'),
('快回','思念','#E58070','坐在小窗边两前爪捧脸，扭头望向外，尾巴绕脚','sits beside a small low windowsill, two front paws cupping cheeks, longing gaze turned to the side, two hind feet tucked naturally, exactly one tail curled around feet, one little coral heart floating'),
('慢行','关心','#A6C867','坐在小车乘客位扣好安全带，一爪做慢一点手势','sits upright in the passenger seat of a tiny mint toy car, diagonal seatbelt clearly visible, one rounded front paw lifted in a gentle slow-down gesture, other front paw rests on seat, hind legs plausibly hidden by car, one tail only and plausibly hidden, caring expression; no driver and no other animal'),
('饿啦','饥饿','#EEA160','抱着空碗坐下，两前爪扶碗，嘴巴微张，尾巴垂侧','sits with both front paws holding one empty cream bowl, hungry pleading gold-brown eyes and slightly open mouth, both hind feet visible, exactly one striped tail resting sideways, three tiny warm orange hunger marks near belly'),
('饭点','好奇','#EEA160','趴桌前一爪托下巴一爪拿小勺，抬眼想菜单','leans at a low simple table, one front paw supports chin, other rounded front paw holds a small spoon, eyes looking upward curiously, hind legs plausibly occluded, a single tail curls beside table, no food text or menu letters'),
('蛋糕','撒娇','#EA92AD','趴着两前爪伸向小蛋糕，亮眼嘴馋，尾巴弯起','lies on belly with both front paws reaching toward one small strawberry cream cupcake on a saucer, wide hopeful gold-brown eyes, tiny tongue peeks out, both hind legs tucked in a natural prone pose, exactly one striped tail curves upward'),
('买好','满足','#75BCB7','坐立两爪抱住小购物袋，满足微笑，尾巴侧弯','sits upright hugging a small pastel teal shopping bag with both rounded front paws, satisfied smile, two hind feet visible, exactly one tail curves to side, one small gold sparkle, bag is blank without logo or text'),
('搞定','自信','#A6C867','侧身坐下一爪高举小绿勾牌，一爪叉腰','sits in a jaunty three-quarter pose, one rounded front paw proudly holds a small green check-mark-shaped token, other front paw rests at waist, hind feet grounded, exactly one curled striped tail, confident relaxed smile, no letters'),
('认可','肯定','#A6C867','站立一爪指向旁边的小物件，另一爪按胸点头','stands in three-quarter view, one rounded front paw extends to present a tiny blank golden star token beside kitten, other paw rests against chest, two hind paws planted, single curved tail, approving warm smile and clear nodding attitude'),
('没有','无辜','#81A9DC','坐直两爪摊开空掌，眉眼无辜，尾巴低垂','sits upright, both rounded front paws lifted and opened outward showing empty pink paw pads in an innocent shrug, hind paws visible, one tail low to side, slightly raised brows and gentle apologetic eyes'),
('倾听','耐心','#75BCB7','身子侧倾一爪靠耳认真听，一爪放膝，尾巴卷脚边','sits with body leaning slightly to one side, one front paw beside ear in a listening gesture, other front paw on knee, two hind feet grounded, exactly one striped tail curled by feet, attentive gold-brown eyes and soft closed smile'),
('思考','沉思','#AE98D4','坐着一爪摸下巴一爪抱胸，眼睛望上，小思考云','sits thoughtfully with one rounded front paw touching chin, other front paw tucked across chest, hind feet visible, exactly one striped tail curling into a loose loop beside body, gaze upward, one small empty pale lavender thought cloud without marks'),
('偷笑','顽皮','#EA92AD','两后爪坐地两前爪捂嘴，眯眼偷笑，尾尖轻翘','sits on hindquarters, both front paws covering lower mouth while eyes squint with a mischievous giggle, two hind feet visible, one striped tail with tip lifted, tiny pink cheeks, no laughter letters'),
('爱你','甜蜜','#EA92AD','两前爪在胸前合成小爱心，粉心贴近爪间','sits upright with both rounded front paws touching gently around one small pink heart at chest level, loving gold-brown eyes and shy smile, two hind feet visible, exactly one tail curled behind; paws remain cat paws not human fingers'),
('小哼','傲娇','#AE98D4','背半转脸侧看，双前爪交抱胸，尾巴甩向另一侧','sits with body half turned away, face glancing sideways with a pout, two front paws crossed against chest, two hind feet grounded, exactly one tail sweeps to opposite side, slightly narrowed gold-brown eyes, playful sulky attitude'),
('震惊','惊讶','#81A9DC','后坐身子微后仰，两爪张开，圆眼张嘴，尾巴僵直','sits leaning backward slightly in surprise, both front paws lifted apart, two hind feet splayed naturally, exactly one tail extending stiffly to side, wide round gold-brown eyes and small open round mouth, tiny blue surprise droplets but no question marks or text'),
('质疑','怀疑','#AE98D4','趴在桌沿一爪托脸，一边眉挑高，另一爪垂着','leans one cheek on one front paw at a low plain tabletop, other front paw hangs lazily over edge, skeptical uneven brows and one slightly narrowed eye, body in three-quarter view, hind legs occluded reasonably, one striped tail visible beside body, no words'),
('盯住','警惕','#E58070','坐立前倾双爪搭膝，眼神斜睨，尾巴紧绕身','sits upright leaning forward, both front paws firmly planted on knees, hind feet visible, exactly one tail wrapped tightly beside body, watchful side-eye and stern but cute expression, one small coral emphasis ray'),
('服气','无奈','#75BCB7','侧躺一爪搭额头另一爪垂落，半睁眼，尾巴平摊','reclines on one side in an exasperated pose, one front paw draped over forehead, other front paw rests loosely downward, two hind legs bent naturally, exactly one striped tail resting flat behind, half-lidded tired gold-brown eyes, small curved sigh puff'),
('冒火','生气','#E58070','蹲坐两爪握紧贴身，眉压低，小橙火在旁但不烧猫','crouches in a compact annoyed sitting pose, both front paws tucked tightly beside chest, hind feet grounded, one striped tail curled rigidly beside body, lowered brows and puffed cheeks, a small harmless stylized orange flame icon beside head, no real burning or text'),
('放空','呆萌','#81A9DC','坐着前爪垂下，眼神放空，头顶小空泡，尾巴成松弯','sits slackly with front paws dangling between knees, hind feet visible, exactly one striped tail in a relaxed curve, blank but cute gold-brown gaze and tiny open mouth, one empty pale blue bubble above head, no writing inside bubble'),
('累啦','疲惫','#AE98D4','趴在小软垫上前爪摊平，下巴压垫，眼半闭，尾巴垂侧','lies flattened on a tiny pale lavender cushion, both front paws stretched flat in front, chin sunk onto cushion, half-closed sleepy eyes, hind legs tucked naturally, exactly one striped tail droops sideways, no sleep letters')
]
assert len(rows)==24 and len({r[0] for r in rows})==24
items=[]
for i,(c,r) in enumerate(zip(captions,rows),1):
    m,e,color,pose,action=r
    items.append({'number':f'{i:02d}','caption':c,'meaning':m,'emotion':e,'pose':pose,'action_en':action,'characters':['奶思'],'text_color':color,'art':f'../02_原画/{i:02d}.png'})
with (V/'01_资料/文案.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['number','caption','meaning','emotion','pose','text_color']);w.writeheader();w.writerows({k:r[k] for k in w.fieldnames} for r in items)
dump(V/'03_工程/动作设计.json',items)
font=Path('/Users/saymagic/Library/Fonts/ZCOOLKuaiLe-Regular.ttf')
job={'title':entry['title'],'description':entry['description'],'characters':['奶思'],'media':'静态','version_id':entry['id'],'items':items,'extras':{'cover':'../02_原画/cover.png','chat_icon':'../02_原画/chat_icon.png','banner':'../02_原画/banner.png'},'style':{'font':str(font),'text_style':'colorful','text_stroke_color':'#433535','text_stroke_radius':6,'text_fill_expand':2,'outline_radius':12,'text_outline_radius':10,'caption_position':'top'}}
dump(V/'03_工程/job.json',job)
for name in ['build_pack.py','validate_pack.py','pack_utils.py']:
    dst=V/'03_工程/导出器'/name;dst.parent.mkdir(exist_ok=True);shutil.copyfile(ROOT/'03_工程'/name,dst)
# Only update this unfinished version's copied exporter; inherited old preview date must not be used.
b=V/'03_工程/导出器/build_pack.py'
b.write_text(b.read_text().replace('已核对2026年10月2日官方公开制作规范','已核对2026年10月3日官方公开制作规范'))
(V/'01_资料/参考与权利来源.md').write_text(f'''# 本次角色与来源\n\n角色为奶思，灰黑虎斑短毛、金棕眼、奶油口鼻、粉鼻；原始卡通基准实际已查看。圆脸、幼猫身形和细软手绘毛纹按基准锁定。\n\n参考由作品库new命令从04_角色素材/奶思/卡通基准.png复制，SHA256：{sha(ref)}。只作为身份和画风依据；本套独立生成新动作，无裁切总览及旧套换字。参考里的英语不复制。用户拥有/提供的参考之完整版权证明未在本任务提供，微信权利及艺术家资料仍须真实平台核验。\n\n原画通过本会话image_gen工具实际生成，模型名称和质量未由工具公开，不作声明。使用真实Alpha透明输出，中文由确定性导出器排版。字体采用ZCOOL KuaiLe（站酷快乐体），许可为SIL OFL 1.1；保留公开来源和许可文本，本套ZIP不包含字体二进制。\n''',encoding='utf-8')
dump(V/'05_验收/任务进度.json',{'local_ready':False,'stage':'原画生成','version_id':entry['id'],'production_writes_stopped':False})
print(json.dumps({'version':str(V),'items':len(items),'reference_sha256':sha(ref)},ensure_ascii=False))
