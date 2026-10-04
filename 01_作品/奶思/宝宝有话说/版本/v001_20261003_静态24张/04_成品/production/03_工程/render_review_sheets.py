"""Render evidence only. This script never sets a visual verdict."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,math
V=Path(__file__).resolve().parent.parent
OUT=V/'04_成品'
QA=V/'05_验收/视觉证据';QA.mkdir(exist_ok=True)
FONT='/Users/saymagic/Library/Fonts/ZCOOLKuaiLe-Regular.ttf'
def bg(size,mode):
 im=Image.new('RGB',size,(248,246,242) if mode!='dark' else (35,38,43))
 if mode=='checker':
  d=ImageDraw.Draw(im)
  for y in range(0,size[1],12):
   for x in range(0,size[0],12):d.rectangle((x,y,x+11,y+11),fill=(215,214,211) if (x//12+y//12)%2 else (250,249,247))
 return im
items=json.loads((OUT/'manifest.json').read_text())
for mode in ['light','dark','checker']:
 for px in [240,120]:
  per_page,cols=(12,4) if px==240 else (24,6)
  for start in range(0,24,per_page):
   subset=items[start:start+per_page];cw=px+24;ch=px+36
   im=bg((cols*cw+24,64+math.ceil(len(subset)/cols)*ch),mode);d=ImageDraw.Draw(im);ink=(247,242,237) if mode=='dark' else (54,43,39)
   d.text((20,16),f'奶思 {mode} 实际 {px}px {start+1:02d}至{start+len(subset):02d}',font=ImageFont.truetype(FONT,24),fill=ink)
   for j,x in enumerate(subset):
    p=OUT/x['main_png' if px==240 else 'thumbnail'];a=Image.open(p).convert('RGBA');assert a.size==(px,px)
    tx,ty=24+(j%cols)*cw,60+(j//cols)*ch;im.paste(a,(tx,ty),a)
    d.text((tx,ty+px+4),x['number']+' '+x['caption'],font=ImageFont.truetype(FONT,16 if px==120 else 20),fill=ink)
   im.save(QA/f'{mode}_{px}_{start+1:02d}.png')
for start in [0,12]:
 im=bg((1080,890),'dark');d=ImageDraw.Draw(im);d.text((20,16),f'奶思 静态GIF 实际240px {start+1:02d}至{start+12:02d}',font=ImageFont.truetype(FONT,24),fill='white')
 for j,x in enumerate(items[start:start+12]):
  a=Image.open(OUT/x['main_gif']).convert('RGBA');tx,ty=24+(j%4)*264,60+(j//4)*276;im.paste(a,(tx,ty),a);d.text((tx,ty+244),x['number']+' '+x['caption'],font=ImageFont.truetype(FONT,20),fill='white')
 im.save(QA/f'gif_240_{start+1:02d}.png')
im=Image.new('RGB',(1020,880),(245,243,239));d=ImageDraw.Draw(im);d.text((20,10),'奶思 配套：封面240px / 图标50px / 横幅750x400',font=ImageFont.truetype(FONT,24),fill=(60,43,35))
for j,mode in enumerate(['light','dark','checker']):
 pan=bg((320,340),mode);cover=Image.open(OUT/'extras/cover_240.png').convert('RGBA');pan.paste(cover,(40,0),cover);icon=Image.open(OUT/'extras/chat_icon_50.png').convert('RGBA');pan.paste(icon,(135,260),icon);im.paste(pan,(20+j*330,60))
banner=Image.open(OUT/'extras/banner_750x400.jpg');assert banner.size==(750,400);im.paste(banner,(135,430));im.save(QA/'extras_actual.png')
print(str(QA))
