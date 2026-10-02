from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
SKILL = Path('/Users/saymagic/.codex/skills/wechat-cat-sticker-pack')

# Each entry is a separate image prompt and native original. References remain intact.
SCENES = [
    'Cheerful morning stretch: chest low, front paws extended, rump raised, one tail curling upward, happy closed-eye smile. A small doodled yellow sun to one side.',
    'Attentive seated kitten holding a tiny blank cream envelope securely between its two front paws, bright interested eyes, tail wrapped along the side. One small blue acknowledgement sparkle.',
    'Kitten seated in a confident three-quarter view, one front paw making a friendly OK-like paw gesture near the cheek, other front paw rests on the ground, warm smile. Two golden sparkles.',
    'A grateful kitten making a little polite bow with both front paws neatly together, eyes softened, head lowered slightly; one small peach heart above its shoulder.',
    'Friendly kitten tilting its head with one front paw touching its chest and the other resting on the ground, smiling reassuringly, one tail loosely curved at the side. One tiny blue sparkle.',
    'Affectionate kitten rubbing its cheek gently against a small peach heart-shaped cushion, eyes blissfully closed, both front paws around the cushion, one curved tail behind. Two tiny pink hearts.',
    'Dreamy kitten seated with both front paws below its chin, gazing upward with sparkling eyes, ears softly relaxed, one tail curled beside it. Two small rose-pink hearts over one shoulder.',
    'Kitten leaning forward with both front legs stretched out inviting an air hug, open gentle eyes, tiny warm smile; one fluffy/striped tail behind and both hind paws naturally supporting its body. A small coral heart.',
    'Laughing kitten rolling sideways on its back, paws naturally tucked toward its belly, eyes squeezed shut and joyful open mouth, one tail visible along its side. Three small orange doodled joy rays.',
    'Excited kitten seated upright with two front paws raised in a thumbs-up-like furry paw gesture, happy confident smile, one tail curved along the side. Two yellow star sparkles.',
    'Energetic kitten in a little determined forward-running leap, front paws reaching forward and hind paws angled back, bright focused eyes, mouth smiling; one tail trailing backward. Two small orange motion strokes, no ground.',
    'Caring kitten offering a small plain pale-blue tea cup resting in a saucer, two front paws hold the saucer securely, body seated and tail beside it, tender smile. A tiny warm heart.',
    'Kitten lifting one front paw palm-forward to ask for a moment, the other front paw planted, wide attentive eyes, mild open mouth, tail resting at its side. Two small blue pause-like doodled rays, no text.',
    'Playful kitten peeking over a small narrow wooden ledge, just upper body and both front paws visible resting on it, head slightly tilted, curious open eyes. One tiny pink doodled exclamation-like ray, no lettering.',
    'Surprised kitten leaning back with huge round eyes and a small O-shaped open mouth, both front paws held close to chest, one tail arched upward behind. Two golden burst rays.',
    'Puzzled kitten tilted three-quarter with head strongly cocked and one front paw touching its cheek, eyes looking sideways, other front paw on the ground, tail visible. Two curved blue doodled question marks without letters.',
    'Sad little kitten sitting low, front paws close together, watery expressive eyes, slightly downturned tiny mouth, ears lowered and one tail curled inward. Two clear pale-blue tear drops at cheeks.',
    'Grumpy kitten crouched low with both front paws pressed forward, brows lowered, ears tilted outward, pouty mouth, single tail curled tensely at its side. A small red hand-drawn anger mark above one ear.',
    'Apologetic kitten seated with head lowered, one front paw rubbing the back of its head and the other resting in front, bashful eyes and tiny sheepish smile, tail tucked close. One small pale-blue sweat drop.',
    'Hungry happy kitten eagerly eating from a small round pale-colored cat-food bowl, both front paws naturally holding the bowl sides, eyes happily closed and tiny pink tongue. One little orange heart, one tail behind. No logo or lettering on bowl.',
    'Very sleepy kitten curled tightly into a small compact ball, face resting on both front paws, eyes peacefully closed, one tail curled around the body; a tiny pale-purple sleepy cloud, no Z letters.',
    'Kitten resting snugly under a soft blue quilt with simple pale stars, both front paws and head on a small pillow, closed peaceful eyes, body and single tail naturally hidden by quilt. Small golden crescent moon and one tiny star.',
    'Kitten waving goodbye with one front paw, other front paw resting naturally, body turned slightly away but head looking back warmly, one tail curves behind it. Two small peach motion strokes.',
    'Happy kitten walking away in three-quarter rear view while looking back with a friendly smile, all visible limbs naturally arranged, one tail raised in a loose curve. A small golden sparkle by the head.',
]

PACKS = [
    {
        'cat': '奶思', 'id': 'naisi', 'title': '奶思日常回应',
        'reference': '奶思/f916344e-49d3-4259-a768-20059517a107.png',
        'identity': 'A gray-and-charcoal striped tabby SHORTHAIR kitten, round face, huge golden-brown eyes, cream muzzle and paws, pink nose, detailed soft short fur. Preserve the exact gray tabby character from the reference; never brown tabby, green eyes or long hair.',
        'captions': '早上好,收到啦,好哒,谢谢你,不客气,来贴贴,想你啦,抱抱,哈哈哈,太棒了,加油呀,辛苦啦,等一下,在吗,真的吗,不懂呀,委屈了,气鼓鼓,我错啦,开饭啦,困困了,晚安,先走啦,明天见'.split(','),
        'description': '灰虎斑奶思把问候、感谢和小情绪变成软萌回应，陪你聊好每一天。',
        'banner_scene': 'Cozy golden morning nook with a peach-colored armchair and an airy sky-blue window. Naisi playfully stretches on a soft rounded rug, with a small potted plant, warm little sunbeams and a toy ball. One cat only, complete cat visible, storytelling composition, pale apricot and muted sky blue colored background, never plain white.',
        'style': {'text_style': 'legacy_coffee', 'ink': '#402319', 'text_outline_radius': 14},
    },
    {
        'cat': '古德', 'id': 'gude', 'title': '古德有话说',
        'reference': '古德/棕色虎斑猫可爱贴纸合集.png',
        'identity': 'A warm brown-and-dark-coffee striped tabby SHORTHAIR kitten, compact round face, enormous vivid GREEN eyes, creamy muzzle and paws, pink-brown nose, detailed soft short fur. Preserve the exact brown tabby character from the reference; never gray tabby, blue eyes or long hair.',
        'captions': '早呀,收到,安排上,谢谢啦,没问题,贴一个,想你了,抱一个,笑哈哈,点赞,冲呀,歇会儿,等会儿,在不在,好家伙,让我想想,委屈,生气了,对不起,干饭啦,困了,晚安啦,拜拜,明天再聊'.split(','),
        'description': '绿眼棕虎斑古德认真接话，也认真撒娇，让日常聊天多一点可爱和热闹。',
        'banner_scene': 'Cheerful mint-and-apricot living-room reading corner. Gude the green-eyed brown tabby sits playfully beside a short stack of blank colorful books and a small toy ball, one front paw waving. Soft rounded shapes, sunny window and plant, complete single cat visible, storybook warmth. Saturated but gentle sage-green colored background, never plain white.',
        'style': {'text_style': 'colorful', 'text_palette': ['#EA7E44','#427EBE','#83AC5C','#C18763','#4B85B9','#DC7993','#B18BCC','#E98B4A'], 'text_stroke_color': '#49352B', 'text_fill_expand': 2, 'text_stroke_radius': 5, 'text_outline_radius': 10},
    },
    {
        'cat': '范恩', 'id': 'fanen', 'title': '范恩软萌日常',
        'reference': '范恩/0d707089-ec57-4d75-8cd2-251fc5da7006.png',
        'identity': 'A fluffy cream-white LONGHAIR ragdoll kitten with enormous clear BLUE eyes, very pale warm-gray point markings on ears and forehead, white muzzle chest and paws, tiny pink nose, fluffy taupe-gray tail. Preserve the exact very light longhaired kitten from the reference; never tabby stripes, black patches, dark Siamese mask or green eyes.',
        'captions': '早安,来啦,好呀,谢谢,没关系,贴贴,想你,抱抱你,笑死啦,好开心,你最棒,陪着你,等等我,求关注,真的吗,听不懂,好委屈,哼哼,原谅我,饿饿,好困哦,晚安呀,回头见,明天见'.split(','),
        'description': '蓝眼长毛猫范恩送来轻轻的问候、甜甜的贴贴和暖暖的陪伴，软萌回应每一句话。',
        'banner_scene': 'Gentle lavender-and-pink cushion corner by a rounded window with tiny twinkling stars. Fanen the fluffy cream-white blue-eyed kitten cuddles a pale pink heart cushion, with a small blue quilt and soft toy nearby. Complete single cat visible, soft watercolor storybook room, colored periwinkle-lavender background, never plain white.',
        'style': {'text_style': 'colorful', 'text_palette': ['#DC9975','#6F91C8','#B296D0','#DD86A5','#90B7C8','#E58D9E','#AB91CF','#69A7BF'], 'text_stroke_color': '#48332E', 'text_fill_expand': 2, 'text_stroke_radius': 5, 'text_outline_radius': 10},
    },
]

FONT = '/System/Library/AssetsV2/com_apple_MobileAsset_Font7/8dc7805506cc9f233dcc19aabf593196842a47ae.asset/AssetData/Hannotate.ttc'
COMMON = ('Create ONE standalone high-resolution square 1280x1280 (or larger) sticker art layer based faithfully on the supplied ORIGINAL character reference sheet. '
          'Match its exact finely detailed hand-drawn watercolor and colored-pencil fur, cute chibi proportions, broad round face, huge expressive eyes and warm playful spirit. '
          'This is an individual original, never a grid, sprite sheet or montage. No photorealism, flat vector art or 3D. '
          'There is ONE cat only, anatomically coherent paws with no duplicate limbs and exactly ONE tail; logically hidden limbs and tail are fine. '
          'Full subject, props and decorative marks visible with about 5 percent clear safety padding; cat fills most of canvas. '
          'Draw NO text, NO letters, NO numbers, NO watermark, NO white sticker outline, NO cast shadow and NO floor. Typography and a smooth white sticker contour will be added separately in final export. '
          'Use truly TRANSPARENT background if possible; otherwise perfectly flat solid #00FF00 chroma-key background with no shadows, texture or gradient. Never green background-colored light or fringe in the cat. ')

def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')

def main():
    engine=ROOT/'03_工程'
    for name in ['build_pack.py','validate_pack.py','pack_utils.py','plan_pack.py']:
        shutil.copy2(SKILL/'scripts'/name,engine/name)
    profile=json.loads((SKILL/'references/platform-profile.json').read_text())
    profile.update(name='wechat-official-20261002-static-conservative',basis_date='2026-10-02',official_rules_verified=True,
                   note='2026-10-02读取官方公开帮助中心页面及其官方脚本，确认静态主图240px、8至24张、封面240px、聊天图标50px、横幅750x400。实际导出采用更小体积上限；缩略图120px、图标240px及单帧GIF作为兼容备用。登录后投稿页与平台审核尚未验证。',
                   official_source='https://sticker.weixin.qq.com/cgi-bin/mmemoticon-bin/readtemplate?t=guide/index.html#/makingSpecifications')
    profile['extras']['cover']['outline']=False
    profile['extras']['chat_icon'].update(file='chat_icon_50.png',size=[50,50],limit=30000,outline=False)
    profile['extras']['chat_icon_compat'].update(file='chat_icon_240_备用.png',size=[240,240],limit=80000,outline=False)
    write(engine/'platform-profile.json',profile)
    registry={'characters':[]}
    for pack in PACKS:
        target=engine/'references'/f"{pack['id']}.png"
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/pack['reference'],target)
        registry['characters'].append({'id':pack['id'],'name':pack['cat'],'aliases':[], 'references':[{'path':f"references/{pack['id']}.png",'role':'current_user_original_cartoon'}]})
    write(engine/'references'/'characters.json',registry)
    config=[]
    for pack in PACKS:
        version=ROOT/'01_作品'/pack['cat']/pack['title']/'版本'/'v001_20261002_静态24张'
        for sub in ['01_资料','02_原画','03_工程','04_成品']:(version/sub).mkdir(parents=True,exist_ok=True)
        input_request={'cats':[pack['cat']],'captions':pack['captions'],'title':pack['title'],'requested_by':'用户明确要求依据当前目录三个原始卡通形象分别制作一套，全部中文文案、参考图框架一致；文案由Codex设计。'}
        write(version/'01_资料'/'input.json',input_request)
        job={'title':pack['title'],'characters':[pack['cat']],
             'items':[{'number':f'{i+1:02d}','caption':caption,'meaning':caption,'characters':[pack['cat']],
                       'scene':SCENES[i],'art':f'../02_原画/{i+1:02d}.png'} for i,caption in enumerate(pack['captions'])],
             'extras':{'cover':'../02_原画/cover.png','chat_icon':'../02_原画/chat_icon.png','banner':'../02_原画/banner.png'},
             'style':{'font':FONT,'outline_radius':12,'caption_position':'top',**pack['style']},
             'description':pack['description'],'tags':['猫咪','可爱','日常','问候','情绪'],
             'artist_name':None,'rights_owner':None,'ai_assisted':True,'reference':str(ROOT/pack['reference'])}
        write(version/'03_工程'/'job.json',job)
        requests=[]
        for i,caption in enumerate(pack['captions']):
            requests.append({'cat':pack['cat'],'kind':'sticker','number':f'{i+1:02d}',
                'target':str(version/'02_原画'/f'{i+1:02d}.png'),'reference':str(ROOT/pack['reference']),
                'transparent':True,'caption':caption,
                'prompt':COMMON+'\nCharacter identity: '+pack['identity']+'\nUnique scene: '+SCENES[i]+'\nIntended Chinese caption (do NOT draw any text): '+caption})
        for kind,scene in [('cover','A friendly seated three-quarter full-body portrait, all paws naturally arranged, one visible tail curled at the side, bright open eyes and a small soft smile. No decorative marks, no text, no white outline.'),('chat_icon','A centered FRONT-VIEW close-up portrait of the kitten HEAD, with only a tiny hint of neck fur. Both ears and full whiskers visible, eye color clearly readable, sweet neutral smile. No paws, no full body, no props, no decoration, no white outline. This icon must remain recognizable at 50 pixels.')]:
            requests.append({'cat':pack['cat'],'kind':kind,'number':kind,'target':str(version/'02_原画'/f'{kind}.png'),
                'reference':str(ROOT/pack['reference']),'transparent':True,
                'prompt':COMMON+'\nCharacter identity: '+pack['identity']+'\nUnique scene: '+scene})
        requests.append({'cat':pack['cat'],'kind':'banner','number':'banner','target':str(version/'02_原画'/'banner.png'),
            'reference':str(ROOT/pack['reference']),'transparent':False,
            'prompt':'Create one independent polished wide LANDSCAPE 1500x800 or larger watercolor storybook banner for a WeChat cat sticker album. Match the supplied original character sheet\'s delicate colored-pencil and watercolor fur and chibi face. '+pack['identity']+'\nScene: '+pack['banner_scene']+'\nNo lettering, Chinese or English, no numbers, no logo, no watermark, no white sticker contour. OPAQUE colored background filling the whole canvas. Single cat only; harmonious wide storybook scene. Keep the whole cat and important props in the middle 75 percent safe area so a 750x400 crop preserves all key details.'})
        write(version/'03_工程'/'generation_requests.json',requests)
        config.append({**pack,'version_dir':str(version),'requests':requests})
    write(engine/'packs.json',config)
    print(json.dumps({'packs':3,'main_originals':72,'auxiliary_originals':9,'root':str(ROOT)},ensure_ascii=False))

if __name__=='__main__':main()
