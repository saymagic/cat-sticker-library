from pathlib import Path
import sys,json,math
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
FONT='/System/Library/AssetsV2/com_apple_MobileAsset_Font7/8dc7805506cc9f233dcc19aabf593196842a47ae.asset/AssetData/Hannotate.ttc'

def background(size,mode):
    color=(247,244,240) if mode=='light' else (36,39,43)
    image=Image.new('RGB',size,color)
    if mode=='checker':
        d=ImageDraw.Draw(image)
        for y in range(0,size[1],12):
            for x in range(0,size[0],12):d.rectangle((x,y,x+11,y+11),fill=(215,211,204) if (x//12+y//12)%2 else (249,247,242))
    return image

def main():
    packs=json.loads((ROOT/'03_工程/packs.json').read_text())
    for p in packs:
        if len(sys.argv)>1 and p['cat'] not in sys.argv[1:]:continue
        out=Path(p['version_dir'])/'04_成品';qa=out/'previews';qa.mkdir(exist_ok=True)
        for mode,size,per_page,cols in [('light',240,12,4),('dark',120,24,6),('checker',120,24,6)]:
            for start in range(0,24,per_page):
                indices=list(range(start,min(24,start+per_page)))
                gap=20;cw=size+gap;ch=size+35
                sheet=background((cols*cw+gap,80+math.ceil(len(indices)/cols)*ch),mode)
                d=ImageDraw.Draw(sheet);ink=(60,43,34) if mode!='dark' else (249,242,234)
                d.text((20,18),f"{p['cat']} {mode} 实际{size}px {start+1:02d}—{indices[-1]+1:02d}",font=ImageFont.truetype(FONT,25,index=2),fill=ink)
                for j,i in enumerate(indices):
                    im=Image.open(out/('main_png' if size==240 else 'thumbnail')/f'{i+1:02d}.png').convert('RGBA')
                    assert im.size==(size,size)
                    x=20+(j%cols)*cw;y=70+(j//cols)*ch
                    sheet.paste(im,(x,y),im)
                    d.text((x,y+size+2),f'{i+1:02d} '+p['captions'][i],font=ImageFont.truetype(FONT,16 if size==120 else 20,index=2),fill=ink)
                sheet.save(qa/f'qa_{mode}_{size}_{start+1:02d}.jpg',quality=95)
        canvas=Image.new('RGB',(1000,800),(246,243,239));draw=ImageDraw.Draw(canvas)
        draw.text((20,15),p['cat']+' 配套图片 240px封面 / 50px图标',font=ImageFont.truetype(FONT,28,index=2),fill=(62,42,32))
        for j,mode in enumerate(['light','dark','checker']):
            panel=background((310,310),mode)
            cover=Image.open(out/'extras/cover_240.png').convert('RGBA');panel.paste(cover,(35,5),cover)
            icon=Image.open(out/'extras/chat_icon_50.png').convert('RGBA');panel.paste(icon,(130,255),icon)
            canvas.paste(panel,(20+j*320,70))
        banner=Image.open(out/'extras/banner_750x400.jpg').convert('RGB');canvas.paste(banner,(125,395))
        canvas.save(qa/'qa_extras.jpg',quality=96)
        print(p['cat'],'QA contact sheets saved')

if __name__=='__main__':main()
