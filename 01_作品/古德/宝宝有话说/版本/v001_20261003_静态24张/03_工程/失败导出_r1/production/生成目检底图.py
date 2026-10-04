#!/usr/bin/env python3
"""Prepare actual-size review evidence. Never writes review conclusions."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

version = Path(__file__).resolve().parent.parent
root = version / '04_成品'
evidence = version / '05_验收/逐张目检底图'
evidence.mkdir(parents=True, exist_ok=True)
job = json.loads((root / 'job.json').read_text())
font = ImageFont.truetype(job['style']['font'], 16)

def background(mode, size):
    im = Image.new('RGBA', (size, size), '#f5f5f5' if mode == 'light' else '#25272b')
    if mode == 'checker':
        im = Image.new('RGBA', (size, size), '#fafafa')
        draw = ImageDraw.Draw(im)
        for y in range(0, size, 10):
            for x in range(0, size, 10):
                if (x // 10 + y // 10) % 2:
                    draw.rectangle((x, y, x + 9, y + 9), fill='#dedede')
    return im

for batch in range(6):
    sheet = Image.new('RGB', (1140, 1120), '#e9e7e4')
    d = ImageDraw.Draw(sheet)
    for row in range(4):
        n = batch * 4 + row + 1
        number = f'{n:02d}'
        y = row * 280
        d.text((8, y + 4), number + ' ' + job['items'][n-1]['caption'] + ' | 240px: 浅 深 棋盘 | 120px: 浅 深 棋盘', font=font, fill='#3d3432')
        for j, mode in enumerate(['light', 'dark', 'checker']):
            bg = background(mode, 240)
            bg.alpha_composite(Image.open(root / 'main_png' / (number + '.png')).convert('RGBA'))
            sheet.paste(bg.convert('RGB'), (8 + j * 246, y + 30))
            sm = background(mode, 120)
            sm.alpha_composite(Image.open(root / 'thumbnail' / (number + '.png')).convert('RGBA'))
            sheet.paste(sm.convert('RGB'), (754 + j * 126, y + 85))
    sheet.save(evidence / f'{batch*4+1:02d}-{batch*4+4:02d}_实际尺寸三底.png')

sheet = Image.new('RGB', (1040, 840), '#e9e7e4')
d = ImageDraw.Draw(sheet)
for j, mode in enumerate(['light', 'dark', 'checker']):
    d.text((12+j*280, 8), '封面240px '+mode, font=font, fill='#3d3432')
    bg = background(mode, 240)
    bg.alpha_composite(Image.open(root/'extras/cover_240.png').convert('RGBA'))
    sheet.paste(bg.convert('RGB'), (12+j*280, 32))
    d.text((12+j*280, 280), '聊天图标50px '+mode, font=font, fill='#3d3432')
    icon=background(mode,50)
    icon.alpha_composite(Image.open(root/'extras/chat_icon_50.png').convert('RGBA'))
    sheet.paste(icon.convert('RGB'),(12+j*280,305))
    # Nearest-neighbour enlargement assists edge review; 50px original is above.
    sheet.paste(icon.convert('RGB').resize((100,100),Image.Resampling.NEAREST),(80+j*280,305))
d.text((12,420),'独立横幅750x400（原尺寸）',font=font,fill='#3d3432')
sheet.paste(Image.open(root/'extras/banner_750x400.jpg').convert('RGB'),(12,445))
sheet.save(evidence/'配套素材_实际尺寸三底.png')
print(str(evidence))
