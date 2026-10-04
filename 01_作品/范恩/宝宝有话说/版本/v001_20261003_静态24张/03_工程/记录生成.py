from pathlib import Path
import sys,json,shutil,hashlib
from PIL import Image
v=Path("/Users/saymagic/workspace/表情包/01_作品/范恩/宝宝有话说/版本/v001_20261003_静态24张")
req=json.loads(sys.argv[1]); ret=json.loads(sys.argv[2]); src=Path(sys.argv[3]); dst=Path(req['destination']); shutil.copy2(src,dst)
im=Image.open(dst); a=im.getchannel('A') if 'A' in im.getbands() else None
ret['generated_native_file']={'path':str(src),'stored_original':str(dst.relative_to(v)),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'bytes':dst.stat().st_size,'size':list(im.size),'mode':im.mode,'alpha_extrema':list(a.getextrema()) if a else None}
ret['request']=req['args']; ret['tool']='image_gen.imagegen'; ret['model']='not_disclosed'; ret['quality']='not_disclosed'
d=v/'03_工程/生成记录';d.mkdir(exist_ok=True);(d/(req['number']+'.json')).write_text(json.dumps(ret,ensure_ascii=False,indent=2)+'\n');print(json.dumps(ret['generated_native_file'],ensure_ascii=False))
from datetime import datetime
from zoneinfo import ZoneInfo
(v/'05_验收/任务进度.json').write_text(json.dumps({'local_ready':False,'stage':'独立无字原画生成','native_art_saved':len(list((v/'02_原画').glob('[0-9][0-9].png'))),'generation_records':len(list((v/'03_工程/生成记录').glob('*.json'))),'updated_at':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'platform':'未投稿'},ensure_ascii=False,indent=2)+'\n')
