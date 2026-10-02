from pathlib import Path
import sys,json,subprocess,shutil
import numpy as np
from PIL import Image
from pack_utils import read_alpha

ROOT=Path(__file__).resolve().parents[1]
HELPER=Path('/Users/saymagic/.codex/skills/.system/imagegen/scripts/remove_chroma_key.py')

def main():
    packs=json.loads((ROOT/'03_工程/packs.json').read_text())
    reports=[]
    for pack in packs:
        if len(sys.argv)>1 and pack['cat'] not in sys.argv[1:]:continue
        v=Path(pack['version_dir']);rows=[]
        for number in [f'{i:02d}' for i in range(1,25)]+['cover','chat_icon']:
            path=v/'02_原画'/f'{number}.png'
            if not path.exists():rows.append({'number':number,'status':'MISSING'});continue
            try:
                im=Image.open(path).convert('RGBA');a=np.array(im.getchannel('A'))
                corners=[int(a[y,x]) for x,y in [(0,0),(im.width-1,0),(0,im.height-1),(im.width-1,im.height-1)]]
                cleaned=False
                if 0<max(corners)<=8:
                    archive=v/'02_原画/低Alpha清理前';archive.mkdir(exist_ok=True)
                    raw=archive/path.name
                    if not raw.exists():shutil.copy2(path,raw)
                    target=path.with_name(path.stem+'_alpha_clean.png')
                    subprocess.run([sys.executable,str(HELPER),'--input',str(path),'--out',str(target),'--key-color','#00ff00','--tolerance','0'],check=True,capture_output=True,text=True)
                    read_alpha(target)
                    shutil.copy2(target,path);target.unlink()
                    cleaned=True
                im=read_alpha(path)
                rows.append({'number':number,'status':'PASS','native_size':list(im.size),'low_alpha_cleanup':cleaned})
            except Exception as e:rows.append({'number':number,'status':'REPAIR','issue':str(e)})
        rows.append({'number':'banner','status':'PASS' if (v/'02_原画/banner.png').is_file() else 'MISSING'})
        report={'cat':pack['cat'],'rows':rows,'status':'PASS' if all(x['status']=='PASS' for x in rows) else 'PENDING'}
        (v/'03_工程/source_preflight.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        reports.append(report)
        print(json.dumps({'cat':pack['cat'],'status':report['status'],'issues':[x for x in rows if x['status']!='PASS'],'cleaned':[x['number'] for x in rows if x.get('low_alpha_cleanup')]},ensure_ascii=False))

if __name__=='__main__':main()
