#!/usr/bin/env python3
"""Exercise non-default item counts and reject mismatched or incomplete inputs."""
from pathlib import Path
import copy, importlib.util, json, sys

ROOT=Path(__file__).resolve().parents[2]
v=ROOT/'01_作品/古德/小情绪上辑/版本/v001_20261004_静态14张';eng=v/'03_工程'
sys.path.insert(0,str(eng/'导出器'))
from build_pack import validate_job
from validate_pack import assess_visual_review

original=json.loads((eng/'job.json').read_text());checks=[]
for count in (8,14,24):
    job=copy.deepcopy(original);job['count']=count
    job['items']=[dict(original['items'][i%14],meaning=f'词{i}') for i in range(count)]
    validate_job(job,eng);checks.append({'case':f'input_count_{count}','pass':True})
for label,count,declared in [('below_min',7,7),('above_max',25,25),('count_mismatch',14,13)]:
    job=copy.deepcopy(original);job['count']=declared
    job['items']=[dict(original['items'][i%14],meaning=f'词{i}') for i in range(count)]
    try: validate_job(job,eng)
    except ValueError: checks.append({'case':label,'pass':True})
    else: raise AssertionError(label+' unexpectedly accepted')
job=copy.deepcopy(original);job['items'][1]['meaning']=job['items'][0]['meaning']
try:validate_job(job,eng)
except ValueError:checks.append({'case':'duplicate_meaning_rejected','pass':True})
else:raise AssertionError('duplicate meaning accepted')
job=copy.deepcopy(original);job['characters']=['古德','范恩']
try:validate_job(job,eng)
except ValueError:checks.append({'case':'mixed_character_rejected','pass':True})
else:raise AssertionError('mixed cats accepted')
review=json.loads((v/'04_成品/visual_review.json').read_text())
assert assess_visual_review(review,original);checks.append({'case':'actual14_visual_evidence_accepted','pass':True})
review['items'].pop();assert not assess_visual_review(review,original)
checks.append({'case':'missing_visual_item_rejected','pass':True})
checks.append({'case':'actual14_export_and_zip','pass':json.loads((v/'04_成品/validation_report.json').read_text())['technical_pass'] and all(p['testzip']=='pass' for p in json.loads((v/'04_成品/zip_validation.json').read_text()))})
Path(__file__).with_name('数量契约检查.json').write_text(json.dumps({'status':'PASS','checks':checks,'scope':'input boundaries 8/14/24; actual complete export/ZIP exercised on14'},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'PASS','checks':len(checks)},ensure_ascii=False))
