#!/usr/bin/env python3
"""只合成真实导出图以供目检，不生成目检结论。"""
from pathlib import Path
import json
import sys
from PIL import Image, ImageDraw, ImageFont

v = Path(sys.argv[1])
root = v / '04_成品'
evidence = v / '05_验收/视觉证据'
evidence.mkdir(parents=True, exist_ok=True)
job = json.loads((root / 'job.json').read_text())
profile = json.loads((root / 'platform-profile.json').read_text())
font = ImageFont.truetype(job['style']['font'], 18)
small = ImageFont.truetype(job['style']['font'], 15)

def background(size, mode):
    colors = {'light': '#F5F4F1', 'dark': '#25272B'}
    im = Image.new('RGB', size, colors.get(mode, '#FAFAFA'))
    if mode == 'checker':
        d = ImageDraw.Draw(im)
        for y in range(0, size[1], 10):
            for x in range(0, size[0], 10):
                if (x // 10 + y // 10) % 2:
                    d.rectangle((x,y,x+9,y+9), fill='#D7D7D7')
    return im

for page in range(6):
    sheet = Image.new('RGB', (1152, 1188), '#E9E2DB')
    d = ImageDraw.Draw(sheet)
    for col, mode in enumerate(('light','dark','checker')):
        d.text((col*384+12, 8), mode + ' · 240px / 120px 原尺寸', font=font, fill='#40352E')
    for row in range(4):
        i = page*4+row
        item = job['items'][i]
        number = f'{i+1:02d}'
        main = Image.open(root/'main_png'/f'{number}.png').convert('RGBA')
        thumb = Image.open(root/'thumbnail'/f'{number}.png').convert('RGBA')
        assert main.size == (240,240) and thumb.size == (120,120)
        for col, mode in enumerate(('light','dark','checker')):
            x,y = col*384+12, row*284+42
            d.text((x,y), number+' '+item['caption'], font=font, fill='#40352E')
            a,b = background(main.size,mode),background(thumb.size,mode)
            a.paste(main,(0,0),main); b.paste(thumb,(0,0),thumb)
            sheet.paste(a,(x,y+26)); sheet.paste(b,(x+248,y+26))
    sheet.save(evidence/f'主图三底原尺寸_{page+1:02}.png')

for page in range(4):
    sheet = Image.new('RGB', (792, 576), '#E9E2DB')
    d = ImageDraw.Draw(sheet)
    for j in range(6):
        i=page*6+j; number=f'{i+1:02}'; x,y=(j%3)*264+12,(j//3)*284+8
        d.text((x,y), number+' 单帧GIF '+job['items'][i]['caption'], font=small,fill='#40352E')
        im=Image.open(root/'main_gif'/f'{number}.gif').convert('RGBA')
        bg=background(im.size,'checker');bg.paste(im,(0,0),im);sheet.paste(bg,(x,y+25))
    sheet.save(evidence/f'GIF原尺寸_{page+1:02}.png')

sheet=Image.new('RGB',(1152,784),'#E9E2DB');d=ImageDraw.Draw(sheet)
for col,mode in enumerate(('light','dark','checker')):
    x=col*384+12
    d.text((x,8), mode+' · 封面240px/图标50px',font=font,fill='#40352E')
    for key,y in [('cover',42),('chat_icon',330),('chat_icon_compat',458)]:
        fname=profile['extras'][key]['file']
        im=Image.open(root/'extras'/fname).convert('RGBA')
        bg=background(im.size,mode);bg.paste(im,(0,0),im);sheet.paste(bg,(x,y))
        d.text((x,y+im.height+4),fname,font=small,fill='#40352E')
sheet.save(evidence/'配套透明素材三底.png')
banner=Image.open(root/'extras'/profile['extras']['banner']['file']).convert('RGB')
assert banner.size==(750,400)
banner.save(evidence/'横幅实际750x400.png')
print(json.dumps({'evidence':str(evidence),'sheets':12,'visual_status':'pending_real_inspection'},ensure_ascii=False))
