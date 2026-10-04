#!/usr/bin/env python3
"""Prepare new, unsealed 14-item versions without editing historical packs."""
from pathlib import Path
import csv, hashlib, json, shutil

ROOT = Path(__file__).resolve().parents[2]
BATCH = Path(__file__).resolve().parent
FONT_SOURCE = ROOT / '01_作品/古德/宝宝有话说/版本/v001_20261003_静态24张/03_工程/字体'
SCENES = [
 ('坏','调皮','#AE98D4','Seated three-quarter view, cheeky asymmetric closed-mouth grin, one front paw resting at cheek as if plotting a little prank, other forepaw planted; one tail curling sideways.'),
 ('嘿嘿嘿','坏笑','#F2C454','Seated facing front, both front paws clasped together below muzzle, shoulders hunched with a cheeky broad toothless grin, eyes narrowed happily, tiny golden chuckle motion ticks; hind paws visible, one tail.'),
 ('看扁我？','不服','#E58070','Standing proudly on two hind paws, chest puffed, chin raised, one forepaw on hip and other forepaw pointing to own chest, determined indignant green or blue eyes, tiny upward energy ticks; entire body and one tail.'),
 ('被看扁了','委屈','#81A9DC','Comically squashed flat as a harmless soft pancake kitten lying low, ears gently folded sideways, sad wide eyes, tiny cheek tear, forepaws extended and hind paws plausibly tucked behind, one tail lying flat. No injury, no person.'),
 ('稍等','等待','#75BCB7','Sitting upright, one forepaw lifted with its soft paw pad toward viewer as a polite wait gesture, other forepaw beside a small blue sand hourglass, patient expression, hind paws and one tail.'),
 ('跳舞','起舞','#EA92AD','Joyful dancing on one hind paw, other hind paw bent lifted, both forepaws raised at different heights, head tilted, open happy mouth, tiny ochre and cyan rhythm confetti and motion curves; one tail.'),
 ('跳','跳跃','#A6C867','An athletic kitten springing upward, all four paws clear and off the ground with forepaws reaching upward and hind legs stretched back, joyful alert expression, small upward motion strokes, one tail arcing below. No floor shadow.'),
 ('冷','怕冷','#81A9DC','Sitting compactly wrapped in a pale blue knitted scarf with both forepaws holding scarf against chest, ears low, chilly worried expression, two simple icy blue snowflakes beside it; hind paws and one curled tail visible.'),
 ('发抖','颤抖','#AE98D4','Entire kitten visibly trembling in a small crouch, forepaws pressed close, hind paws tucked, wide anxious eyes and slightly quivering mouth, several short cyan zigzag tremble marks around body, one tail tight beside body. No scarf; distinct from cold pose.'),
 ('热','怕热','#EEA160','Sitting slumped with hind paws stretched out, tongue slightly out, one forepaw slowly holding a cream paper fan and the other forepaw on belly, tiny orange warm air curls and a sweat drop, one tail relaxed sideways.'),
 ('淋雨','落汤猫','#81A9DC','A wet kitten huddling sadly, fur clumped but character identity preserved, ears down, front paws close, hind paws tucked, one drooping tail; a small blue rain cloud above and several clearly separated opaque blue rain drops. No broad background or floor.'),
 ('摸摸头','安慰','#EA92AD','Sweet kitten softly patting its own head with one clearly feline front paw, other forepaw planted, eyes happily closed and tiny blush, sitting with both hind paws plausible, one curved tail, two small coral hearts. No human hand and no second animal.'),
 ('吐血','扎心','#E58070','A melodramatic shocked kitten slumped backward sitting, one forepaw pressed to chest and the other supporting its body, one tiny stylized coral-red drop from corner of mouth and a red zigzag comic reaction symbol. Harmless cartoon reaction, no wounds, no gore, no realistic blood pool; one tail.'),
 ('呆住','愣住','#75BCB7','Sitting bolt upright completely frozen, perfectly wide round eyes, small open mouth, both front paws straight and parallel, hind paws tucked, ears perked, tail stiff sideways, two small yellow surprise dashes. No text.'),
 ('勃然小怒','微怒','#E58070','Kitten sulking mildly with cheeks slightly puffed and brows knit, seated with both front paws folded together at chest, one tiny coral comic anger tick near ear, hind paws and one tail. Small restrained anger, cute rather than scary.'),
 ('小发雷霆','发怒','#EEA160','Comically furious but cute kitten standing upright on hind paws, mouth open in a tiny shout, both forepaws lifted in small clenched mitten paws, one tail standing curved, several orange lightning bolt doodles and motion ticks. Stronger energy than mild sulking, no weapons, no fire background.'),
 ('捶你','轻捶','#E58070','A playful kitten leaning forward in three-quarter view, one front paw reaching toward viewer as a soft mitten-paw boop/punch and other forepaw braced, mischievous focused face, hind paws grounded, one tail curved behind, small yellow impact star near paw. No human fist, no second character, no injury.'),
 ('困了','困倦','#AE98D4','Kitten yawning widely with half-closed sleepy eyes, sitting and leaning head into one forepaw while other forepaw holds a tiny lavender pillow; hind paws and one curled tail. No letter Z, no text.'),
 ('哦。','平淡','#81A9DC','Deadpan sitting kitten with half-lidded eyes and a tiny straight relaxed mouth, both front paws evenly planted, hind paws tucked, one tail quietly curling beside it. Minimal props, understated unimpressed emotion.'),
 ('OK','答应','#A6C867','Bright friendly kitten nodding and raising one feline forepaw with pink paw pad visible in acknowledgement, other forepaw planted, joyful eyes, small golden checkmark shape beside it, hind paws and one tail. No human fingers, no letters; OK will be typeset later.'),
 ('笑','开心','#F2C454','Kitten laughing heartily, eyes closed in crescent smiles, mouth open joyfully, sitting slightly leaning back, one forepaw pressed to belly and the other waving, hind paws relaxed, one tail; small golden laughing motion rays.'),
 ('kiss','亲亲','#EA92AD','Kitten blowing a sweet kiss, eyes softly closed, puckered small mouth, one forepaw at lips and other forepaw resting, three small coral hearts drifting outward, sitting with hind paws and one curled tail. No letters; kiss will be typeset later.'),
 ('撅嘴','嘟嘴','#EA92AD','Kitten turning head slightly sideways with a clearly pouty puckered mouth, cheeks puffed, both forepaws crossed in front of chest, raised brows and small pink blush, hind paws and one tail, no hearts. Different from kiss pose.'),
 ('三分冷漠','冷漠','#81A9DC','Cool detached kitten seated on LEFT half of canvas, head turned slightly away with half-lidded eyes, front paws together and one tail on left, RIGHT half kept entirely empty for an exact 30 percent pie chart added as a native diagram during export. No chart drawn in source, no text.'),
 ('炸弹','炸弹','#AE98D4','Alarmed kitten holding one harmless toy round charcoal cartoon bomb with a tiny golden fuse spark, front paws supporting bomb carefully, eyes wide, seated with hind paws, one tail. Cute symbolic sticker, no explosion, no weapon instructions.'),
 ('心虚','心虚','#EEA160','Guilty sheepish kitten glancing sideways, one forepaw hiding behind back and other forepaw touching cheek, ears low, a tiny blue sweat drop on forehead, awkward tight mouth, hind paws and one tail.'),
 ('流汗','尴尬','#75BCB7','Embarrassed kitten seated facing viewer, large opaque blue sweat drops by forehead and cheek, one forepaw wiping brow and other supporting body, nervous small smile, hind paws and one curled tail. Distinct from guilty sideways glance.'),
 ('咪','卖萌','#EA92AD','Ultra sweet kitten curling both forepaws close to cheeks, head tilted, very bright wide eyes and small smiling mouth, soft pink cheek blush, sitting with both hind paws visible and one fluffy or striped tail curled, two small coral hearts. No text.'),
]
REQUEST = '完成古德和范恩各一套表情包的制作，文案为：1. 坏 2. 嘿嘿嘿 3.看扁我？ 4.被看扁了 5.稍等 6.跳舞 7.跳 8.冷 9.发抖 10.热 11.淋雨 12. 摸摸头 13.吐血 14.呆住 15.勃然小怒 16.小发雷霆 17.捶你 18.困了 19.哦。 20.OK 21.笑 22.kiss 23.撅嘴 24.三分冷漠（扇形图） 25.炸弹 26.心虚 27.流汗 28.咪（卖萌）'

def dump(p, data): p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

entries=json.loads((ROOT/'作品目录.json').read_text())['entries']
batch=[]
for e in entries:
    if e['theme'] not in ('小情绪上辑','小情绪下辑'): continue
    v=ROOT/e['path']; eng=v/'03_工程'; cat=e['character']; first=0 if e['theme']=='小情绪上辑' else 14
    identity = ('warm brown SHORT-haired tabby kitten, green eyes, clear dark brown forehead, cheek, body and tail stripes, pink nose, cream muzzle and paws'
                if cat=='古德' else 'pale ivory cream-white LONG-haired fluffy kitten, blue eyes, pale grey-taupe ears and ONE grey-taupe fluffy tail, pink nose and pink paw pads, no dark tabby stripes')
    (v/'01_资料/用户原始需求.md').write_text('# 本次用户原文\n\n'+REQUEST+'\n\n按作品库8至24张约束分两辑，每辑14张，不增删不改变原顺序。括号中的扇形图/卖萌作为动作指令；OK和kiss按用户原文保留。\n')
    (v/'01_资料/参考与权利来源.md').write_text(f'# 参考与权利来源\n\n本版角色为{cat}。引用本库04_角色素材/{cat}/卡通基准.png，复制进本版01_资料/参考/卡通基准.png，保持身份和手绘画风。原画以本版快照为身份参考独立生成，不复用其他主题动作。参考原始权利依据沿用库中已有记录；未确认的艺术家身份、授权和平台审核没有新增结论。字体为ZCOOL KuaiLe，SIL OFL 1.1，字体二进制不进入投稿或完整制作备份。\n\n参考SHA256：{sha(v/"01_资料/参考/卡通基准.png")}\n')
    dump(v/'01_资料/角色快照.json',{'schema_version':1,'character':cat,'identity':identity,'reference':str(v/'01_资料/参考/卡通基准.png'),'sha256':sha(v/'01_资料/参考/卡通基准.png'),'reference_basis':'库内卡通基准；已实际查看毛色、眼色、毛长及参考框架','style':'watercolor/gouache textured hand-painted kitten; caption above, cat below, white contour on main only'})
    for fname in ('ZCOOLKuaiLe-Regular.ttf','OFL.txt','字体说明.md'):
        shutil.copy2(FONT_SOURCE/fname,eng/'字体'/fname)
    shutil.copy2(ROOT/'01_作品/古德/小情绪上辑/版本/v001_20261004_静态14张/03_工程/接收与透明处理.py',eng/'接收与透明处理.py') if cat!='古德' or first else None
    items=[]; tasks=[]
    for local,(caption,meaning,color,scene) in enumerate(SCENES[first:first+14],1):
        number=f'{local:02d}'; global_number=first+local
        specific=scene.replace('green or blue eyes','green eyes' if cat=='古德' else 'blue eyes')
        prompt=f'''Use case: illustration-story. Asset: one single INDEPENDENT high-resolution original artwork for cat reaction sticker {global_number}; no grid, collage or contact sheet.
Input reference is ONLY the identity and hand-painted style guide. Generate a NEW pose of {cat}: {identity}. Preserve the reference face and ordinary kitten proportions, hand-painted watercolor/gouache textured fur and compact warm expressive design.
Scene and pose: {specific}
Reaction intent: “{caption}”. DO NOT draw that text or any other letters/numbers; the exact caption will be typeset later.
Composition: ONE cat only, full body and ONE tail inside a square canvas, 10 percent clear padding, opaque crisp illustrated fur edges, all paws anatomically plausible. For the pie-chart asset keep the RIGHT half empty and cat on left; otherwise center the whole subject. No human hands, no second animal, no watermark, no white sticker border.
Background: perfectly flat solid #FF00FF magenta chroma-key background for local removal, no gradients, texture, floor, cast/contact shadows; avoid saturated magenta within subject. At least 1024x1024 native original.
'''
        # The already generated first sample has its exact prompt retained separately.
        if not (cat=='古德' and first==0 and local==1): (eng/'提示词'/f'{number}.txt').write_text(prompt)
        items.append({'number':number,'user_number':global_number,'caption':caption,'meaning':meaning,'characters':[cat],'text_color':color,'pose':specific,'art':f'../02_原画/{number}.png','pie_chart':global_number==24})
        tasks.append({'asset':number,'user_number':global_number,'caption':caption,'prompt':str(eng/'提示词'/f'{number}.txt')})
    for asset,scene in [
        ('cover','A full-body kitten standing sweetly with one front paw raised in a friendly wave, other front paw planted, hind paws and one tail fully visible; cheerful smile. No caption, no white outline.'),
        ('chat_icon','A clear close-up head and shoulders portrait, both full ears inside frame, large recognizable bright eyes and pink nose; upper chest and very top of front paws only. NOT a pure disembodied head, NOT full body. No white outline.'),
        ('banner','Independent wide horizontal 15:8 composition on a complete pale peach, cream and soft sky-blue pastel painted background, a single happy kitten on right waving with one front paw, one tail fully visible; sparse tiny colored hearts, sun and blue rain-drop doodles suggest a range of little emotions. Calm generous left-side empty space; NO TEXT or letters and NO white sticker contour. Entire face ears and tail inside central safe region.')]:
        backdrop='Opaque designed pastel background, not chroma key. Landscape at least 1536x1024.' if asset=='banner' else 'Perfectly flat uniform solid #FF00FF magenta chroma-key background, no shadows, floor or texture; no saturated magenta in kitten. Square at least 1024x1024.'
        prompt=f'Use case: illustration-story. One INDEPENDENT original {asset} artwork for {cat} cat reaction pack. Reference image supplies kitten identity and watercolor/gouache painted style only. Kitten identity: {identity}. {scene} ONE cat only, anatomically plausible feline paws, at most one tail, original proportions; 10% safe padding. No human hands, no extra cat, no words, letters, numbers, watermark or grid. {backdrop}\n'
        (eng/'提示词'/f'{asset}.txt').write_text(prompt);tasks.append({'asset':asset,'prompt':str(eng/'提示词'/f'{asset}.txt')})
    job={'title':e['title'],'description':e['description'],'characters':[cat],'count':14,'user_sequence_range':[first+1,first+14],'items':items,'extras':{x:f'../02_原画/{x}.png' for x in ['cover','chat_icon','banner']},'style':{'font':str(eng/'字体/ZCOOLKuaiLe-Regular.ttf'),'text_style':'colorful','text_stroke_color':'#433535','text_stroke_radius':6,'text_fill_expand':2,'outline_radius':12,'text_outline_radius':10,'caption_position':'top'}}
    dump(eng/'job.json',job);dump(eng/'生成任务.json',tasks)
    with (v/'01_资料/文案.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['number','user_number','caption','meaning','pose']);w.writerows([i['number'],i['user_number'],i['caption'],i['meaning'],i['pose']] for i in items)
    (eng/'本版制作计划.md').write_text(f'# {e["title"]}\n\n14张静态；用户序号{first+1}至{first+14}。使用本版锁定卡通参考，不用技能照片。逐张原生独立生成，无字透明原画，经内置image_gen与安装的chroma-key helper去底；彩色圆润字、深描边、白外沿。工程提供支持8至24张的适配导出器，本版实际14张。第24条扇形图在排版阶段画精确108度扇区，占30%。三底色240px/120px及封面、50px图标、横幅均需真实逐项目检后才记passed。后续ZIP、finish、refresh、deep check、Release、站点与真实下载验收。\n')
    (eng/'上传填写文案.md').write_text(f'# {e["title"]}\n\n专辑名：{e["title"]}\n角色：{cat}\n数量：14张静态，用户原序号{first+1}至{first+14}\n介绍：{e["description"]}\n\n'+''.join(f'{i["number"]}. {i["caption"]}（含义：{i["meaning"]}；原序号{i["user_number"]}）\n' for i in items)+'\nPNG投稿包为主要素材，GIF包是单帧静态兼容格式；尚未微信投稿或审核。艺术家/权利账户填写真实资料，本工程不虚构。\n')
    batch.append({'id':e['id'],'cat':cat,'version':str(v),'tasks':tasks})
dump(BATCH/'生成批次.json',batch)
print(json.dumps([{'cat':x['cat'],'version':x['version'],'tasks':len(x['tasks'])} for x in batch],ensure_ascii=False))
