"""Workflow tests use a temporary library and synthetic test-only images/evidence."""
import contextlib
import copy
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from types import SimpleNamespace

from PIL import Image, ImageDraw
import sticker_library as lib

ROOT = Path(__file__).resolve().parents[1]


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        (self.root / 'scripts/templates').mkdir(parents=True)
        for file in ('scripts/library_config.json', 'scripts/templates/library.html', '03_工程/platform-profile.json'):
            target = self.root / file; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / file, target)
        for cat in ('奶思', '古德', '范恩'):
            file = self.root / f'04_角色素材/{cat}/卡通基准.png'
            file.parent.mkdir(parents=True)
            Image.new('RGBA', (32, 32), (80, 70, 50, 255)).save(file)
        self.config = lib.configuration(self.root)
        self.data = {'schema_version': 2, 'entries': []}

    def tearDown(self):
        self.temp.cleanup()

    def create(self, **kwargs):
        options = dict(cat='奶思', theme='测试日常', title=None, type='静态', count=8, date='20261002', description='用于隔离工作流测试的合成样例。', tag=['测试'], reference=None, copy_exception=None)
        options.update(kwargs)
        return lib.new_entry(self.root, self.data, self.config, SimpleNamespace(**options))

    def fixture(self):
        """Synthetic acceptance records simulate external reviewed input, never real art QA."""
        e = self.create(); version = self.root / e['path']; out = version / '04_成品'
        for folder in ('main_png', 'sources', 'extras'):(out / folder).mkdir()
        manifest, assets = [], []
        captions = ['早安', '谢谢', '抱抱', '收到', '晚安', '加油', '委屈', '拜拜']
        def asset(file, size, color, opaque=False):
            im = Image.new('RGB' if opaque else 'RGBA', tuple(size), color if opaque else (0, 0, 0, 0))
            if not opaque:ImageDraw.Draw(im).ellipse((5, 5, size[0]-6, size[1]-6), fill=(*color, 255))
            path = out / file; im.save(path)
            assets.append({'file':file,'sha256':lib.sha(path),'bytes':path.stat().st_size,'size':size})
        for i, caption in enumerate(captions, 1):
            n = f'{i:02d}'; asset(f'main_png/{n}.png', [240, 240], (20+i*10, 110, 90))
            shutil.copy2(out / f'main_png/{n}.png', out / f'sources/{n}.png')
            shutil.copy2(out / f'sources/{n}.png', version / f'02_原画/{n}.png')
            manifest.append({'number':n,'caption':caption,'meaning':caption,'characters':['奶思'],'source':f'sources/{n}.png','main_png':f'main_png/{n}.png'})
        asset('extras/cover_240.png',[240,240],(110,90,70))
        asset('extras/chat_icon_50.png',[50,50],(90,100,70))
        asset('extras/banner_750x400.jpg',[750,400],(180,210,170),True)
        profile = {'official_rules_verified':True,'basis_date':'2026-10-02','main_png':{'size':[240,240],'format':'PNG','limit':500000,'alpha':True},'extras':{}}
        for key, file, size, fmt, alpha in [('cover','cover_240.png',[240,240],'PNG',True),('chat_icon','chat_icon_50.png',[50,50],'PNG',True),('banner','banner_750x400.jpg',[750,400],'JPEG',False)]:
            profile['extras'][key]={'file':file,'size':size,'format':fmt,'alpha':alpha,'limit':500000}
        lib.save(out/'manifest.json',manifest)
        lib.save(out/'job.json',{'characters':['奶思'],'title':e['title'],'description':e['description'],'items':manifest})
        lib.save(out/'platform-profile.json',profile)
        lib.save(out/'validation_report.json',{'technical_pass':True,'checks':[{'pass':True,'check':'synthetic fixture only'}],'assets':assets})
        lib.save(out/'visual_review.json',{'status':'passed','reviewer':'test fixture only - not actual visual review','issues':[],'background_modes':['light','dark','checker'],'actual_size_px':[240],
                 'items':[{'number':x['number'],**{k:True for k in ('identity','anatomy','caption','outline','pose','readability')}} for x in manifest],
                 'asset_sha256':{x['file']:x['sha256'] for x in assets},'extras':{'cover':True,'chat_icon':True,'banner':True}})
        lib.save(out/'preview.html','<img src="main_png/01.png" alt="隔离测试">')
        stream=io.StringIO();writer=csv.writer(stream);writer.writerow(['number','caption','meaning']);writer.writerows((x['number'],x['caption'],x['meaning']) for x in manifest)
        lib.save(out/'captions.csv',stream.getvalue())
        lib.save(out/'上传填写文案.md','仅用于隔离测试，不是投稿物料。')
        packs=[]
        for name in ('submission_PNG.zip','complete_delivery.zip'):
            with zipfile.ZipFile(out/name,'w') as z:
                if name.startswith('submission'):
                    packed=[]
                    for x in manifest:
                        z.write(out/x['main_png'],'main/'+x['number']+'.png')
                        packed.append({**x,'main':'main/'+x['number']+'.png'})
                    z.writestr('manifest.json',json.dumps(packed,ensure_ascii=False))
                    for x in (out/'extras').iterdir():z.write(x,'extras/'+x.name)
                else:
                    for x in out.rglob('*'):
                        if x.is_file() and x.suffix!='.zip':z.write(x,x.relative_to(out).as_posix())
            packs.append({'file':name,'sha256':lib.sha(out/name)})
        lib.save(out/'zip_validation.json',packs)
        return e

    def complete(self, e):
        gate=lib.acceptance(self.root,e);lib.seal_version(self.root,e,gate);e['status']='本地成品';lib.set_current(self.data,e)

    def material_fixture(self, preview_copy_link=False, cats=None):
        """Synthetic role material, including explicit test-only visual evidence."""
        cats = cats or ['范恩']
        folder = cats[0] if len(cats) == 1 else '共用'
        relative = f'04_角色素材/{folder}/赞赏配套/v001_20261004'
        version = self.root / relative
        for folder in self.config['sections']:
            (version / folder).mkdir(parents=True)
        out = version / '04_成品'
        Image.new('RGB', (30, 20), (240, 225, 210)).save(out / 'guide.png')
        digest = lib.sha(out / 'guide.png')
        lib.save(out / 'manifest.json', [{'file': 'guide.png', 'label': '测试引导图', 'spec': {'size': [30, 20], 'format': 'PNG', 'alpha': False, 'limit': 500000}}])
        lib.save(out / 'validation_report.json', {'technical_pass': True, 'checks': [{'pass': True}], 'assets': [{'file': 'guide.png', 'sha256': digest}]})
        lib.save(out / 'visual_review.json', {'status': 'passed', 'reviewer': 'test fixture only', 'issues': [], 'asset_sha256': {'guide.png': digest}, 'items': {'guide.png': True}})
        lib.save(out / 'preview.html', '<img src="guide.png" alt="隔离测试">' + ('<a href="赞赏引导语.md">查看文案</a>' if preview_copy_link else ''))
        lib.save(out / '赞赏引导语.md', '仅用于隔离测试。')
        with zipfile.ZipFile(out / 'submission_角色配套.zip', 'w') as archive:
            archive.write(out / 'guide.png', 'guide.png')
        lib.save(out / 'zip_validation.json', [{'file': 'submission_角色配套.zip', 'label': '素材下载包', 'sha256': lib.sha(out / 'submission_角色配套.zip')}])
        return lib.register_materials(self.root, self.data, self.config, SimpleNamespace(cat=cats[0], with_cat=cats[1:], path=relative, title='测试赞赏配套'))

    def test_shared_materials_use_existing_roles_without_new_character(self):
        cats = ['古德', '范恩', '奶思']
        material = self.material_fixture(cats=cats)
        self.assertEqual(material['characters'], cats)
        self.assertEqual(material['character'], '古德、范恩、奶思')
        self.assertEqual(set(self.config['characters']), set(cats))
        self.assertEqual(lib.hydrate_materials(self.root, self.data, self.config), [material])
        lib.refresh(self.root, self.data, self.config)
        self.assertIn('共用', material['path'])
        with self.assertRaises(ValueError):
            lib.register_materials(self.root, self.data, self.config, SimpleNamespace(cat='奶思', with_cat=['乃斯'], path='04_角色素材/共用/重复', title='重复'))

    def test_role_materials_preserve_pack_seals_and_reject_changes(self):
        entry = self.fixture(); self.complete(entry)
        seal = self.root / entry['path'] / entry['completion']['seal']
        before = lib.sha(seal)
        material = self.material_fixture()
        lib.refresh(self.root, self.data, self.config)
        self.assertEqual(before, lib.sha(seal))
        self.assertEqual(lib.hydrate_materials(self.root, self.data, self.config), [material])
        with self.assertRaises(ValueError):
            lib.register_materials(self.root, self.data, self.config, SimpleNamespace(cat='范恩', path=material['path'], title='重复登记'))
        (self.root / material['assets'][0]['path']).write_bytes(b'changed')
        with self.assertRaises(ValueError):
            lib.hydrate_materials(self.root, self.data, self.config)

    def test_alias_and_monotonic_versions(self):
        first=self.create(cat='灰虎斑猫'); second=self.create(cat='乃斯',type='动态')
        self.assertEqual(first['character'],'奶思');self.assertEqual(second['sequence'],2)
        self.assertNotEqual(first['id'],second['id']);self.assertTrue((self.root/first['path']).is_dir())
        lib.validate_registry(self.root,self.data,self.config)

    def test_invalid_input_creates_no_orphan(self):
        for kw in ({'cat':'第四只猫'},{'theme':'../越界'},{'count':7},{'title':'超过八个汉字的专辑名称'},{'description':'长'*81},{'reference':'missing.png'}):
            with self.assertRaises(ValueError):self.create(**kw)
        self.assertEqual(self.data['entries'],[]);self.assertFalse((self.root/'01_作品').exists())

    def test_draft_never_replaces_ready_version(self):
        ready=self.fixture();self.complete(ready);draft=self.create()
        output=lib.refresh(self.root,self.data,self.config)
        self.assertEqual(output['status'],'PASS');self.assertTrue(ready['current']);self.assertFalse(draft['current'])
        self.assertEqual(lib.hydrate(self.root,ready,self.config)['health']['state'],'有效')

    def test_unfinished_version_layout_survives_git_checkout(self):
        e = self.create()
        lib.refresh(self.root, self.data, self.config)
        for section in self.config['sections']:
            self.assertTrue((self.root / e['path'] / section / '.gitkeep').is_file())
        def git(*args):
            return subprocess.run(['git', *args], cwd=self.root, check=True,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        git('init', '-q', '-b', 'main')
        git('config', 'user.name', 'Isolated test')
        git('config', 'user.email', 'test@example.invalid')
        git('add', '--', e['path'], lib.CATALOG, 'scripts/library_config.json')
        git('commit', '-qm', 'Synthetic draft layout only')
        with tempfile.TemporaryDirectory() as directory:
            checkout = (Path(directory) / 'checkout').resolve()
            git('clone', '-q', str(self.root), str(checkout))
            lib.validate_registry(checkout, lib.load(checkout / lib.CATALOG),
                                  lib.configuration(checkout))
            self.assertFalse(lib.hydrate(checkout, e, self.config)['can_download'])

    def test_draft_caption_csv_refresh_preserves_copy_and_disables_downloads(self):
        e = self.create()
        copy_path = self.root / e['path'] / '01_资料/文案.csv'
        captions = ['早上好', '哥哥呢', '宝宝到咯', '饿饿！', '已买', '欧了', '啊？？', '你认真的？']
        for headers in (['number', 'caption', 'meaning'], ['编号', '中文文案', '含义词']):
            with self.subTest(headers=headers):
                with copy_path.open('w', encoding='utf-8-sig', newline='') as stream:
                    writer = csv.writer(stream); writer.writerow(headers)
                    writer.writerows((f'{i:02d}', caption, str(i)) for i, caption in enumerate(captions, 1))
                self.assertEqual(lib.refresh(self.root, self.data, self.config)['status'], 'PASS')
                view = lib.hydrate(self.root, e, self.config)
                self.assertEqual([x['caption'] for x in view['items']], captions)
                self.assertEqual([x['number'] for x in view['items']], [f'{i:02d}' for i in range(1, 9)])
                self.assertTrue(all(x['image'] is None for x in view['items']))
                self.assertFalse(view['can_download'])
                self.assertIn('你认真的？', (self.root / lib.PAGE).read_text())

    def test_missing_visual_review_blocks_finish(self):
        e=self.fixture();out=self.root/e['path']/'04_成品';visual=lib.load(out/'visual_review.json');visual['items'][3]['anatomy']=False;lib.save(out/'visual_review.json',visual)
        with self.assertRaisesRegex(ValueError,'视觉复核'):lib.acceptance(self.root,e)
        self.assertEqual(e['status'],'制作中')

    def test_package_content_must_match_actual_main(self):
        e=self.fixture();out=self.root/e['path']/'04_成品';path=out/'submission_PNG.zip'
        with zipfile.ZipFile(path) as z:content={n:z.read(n) for n in z.namelist()}
        content['main/01.png']=content['main/02.png']
        with zipfile.ZipFile(path,'w') as z:
            for n,b in content.items():z.writestr(n,b)
        record=lib.load(out/'zip_validation.json');record[0]['sha256']=lib.sha(path);lib.save(out/'zip_validation.json',record)
        with self.assertRaisesRegex(ValueError,'主图与成品不符'):lib.acceptance(self.root,e)

    def test_changed_completed_asset_disables_download(self):
        e=self.fixture();self.complete(e);file=self.root/e['path']/'04_成品/main_png/01.png';file.write_bytes(file.read_bytes()+b'changed')
        view=lib.hydrate(self.root,e,self.config)
        self.assertEqual(view['display_status'],'需复检');self.assertFalse(view['can_download'])

    def test_deep_check_catches_same_size_same_timestamp_change(self):
        e=self.fixture();self.complete(e);file=self.root/e['path']/'02_原画/01.png';stat=file.stat();content=bytearray(file.read_bytes());content[-1]^=1;file.write_bytes(content);os.utime(file,ns=(stat.st_atime_ns,stat.st_mtime_ns))
        self.assertEqual(lib.integrity(self.root,e)['state'],'有效')
        self.assertEqual(lib.integrity(self.root,e,True)['state'],'需复检')

    def test_git_checkout_timestamp_change_preserves_content_lock(self):
        e=self.fixture();self.complete(e)
        version=self.root/e['path'];seal_path=version/'05_验收/完成锁定.json';original_seal=seal_path.read_bytes()
        for file in lib.protected_files(version):
            stat=file.stat();os.utime(file,ns=(stat.st_atime_ns,stat.st_mtime_ns+1_000_000_000))
        self.assertEqual(lib.integrity(self.root,e)['state'],'有效')
        self.assertEqual(lib.integrity(self.root,e,True)['state'],'有效')
        self.assertEqual(seal_path.read_bytes(),original_seal)
        file=version/'02_原画/01.png';content=bytearray(file.read_bytes());content[-1]^=1;file.write_bytes(content)
        self.assertEqual(lib.integrity(self.root,e)['state'],'需复检')

    def test_unregistered_version_is_rejected(self):
        e=self.create();(self.root/e['path']).parent.joinpath('v099_20261002_静态8张').mkdir()
        with self.assertRaisesRegex(ValueError,'未登记'):lib.validate_registry(self.root,self.data,self.config)

    def test_safe_paths_and_script_embedding(self):
        e=self.create(tag=['</script>测试']);lib.refresh(self.root,self.data,self.config)
        page=(self.root/lib.PAGE).read_text();self.assertNotIn('"tags": ["</script>',page);self.assertIn('\\u003c/script>',page)
        with self.assertRaises(ValueError):lib.inside(self.root,'../escape')
        with self.assertRaises(ValueError):lib.inside(self.root,'/tmp/escape')

    def test_concurrent_new_commands_do_not_collide(self):
        lib.save(self.root/lib.CATALOG,self.data)
        command=[sys.executable,str(ROOT/'scripts/sticker_library.py'),'--root',str(self.root),'new','--cat','奶思','--theme','同时创建','--count','8','--date','20261002']
        first=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        second=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        for process in (first,second):
            output,error=process.communicate(timeout=20)
            self.assertEqual(process.returncode,0,error);self.assertEqual(json.loads(output)['status'],'PASS')
        records=lib.load(self.root/lib.CATALOG)['entries']
        self.assertEqual(sorted(x['sequence'] for x in records),[1,2]);self.assertEqual(len({x['id'] for x in records}),2)

    def test_finish_command_locks_and_refuses_same_version_rewrite(self):
        e=self.fixture();lib.save(self.root/lib.CATALOG,self.data)
        command=[sys.executable,str(ROOT/'scripts/sticker_library.py'),'--root',str(self.root),'finish','--path',e['id'],'--current']
        result=subprocess.run(command,text=True,capture_output=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        completed=lib.load(self.root/lib.CATALOG)['entries'][0]
        self.assertEqual(completed['status'],'本地成品');self.assertTrue(completed['current'])
        self.assertEqual(lib.integrity(self.root,completed,True)['state'],'有效')
        again=subprocess.run(command,text=True,capture_output=True,timeout=20)
        self.assertNotEqual(again.returncode,0);self.assertIn('新版本',again.stderr)

    def test_copy_csv_mismatch_is_rejected(self):
        e=self.fixture();lib.save(self.root/e['path']/'04_成品/captions.csv','number,caption,meaning\n01,错字,错字\n')
        with self.assertRaisesRegex(ValueError,'CSV'):lib.acceptance(self.root,e)

    def test_platform_approval_requires_evidence(self):
        e=self.fixture();self.complete(e);lib.save(self.root/lib.CATALOG,self.data)
        result=subprocess.run([sys.executable,str(ROOT/'scripts/sticker_library.py'),'--root',str(self.root),'platform','--path',e['id'],'--state','审核通过'],text=True,capture_output=True,timeout=20)
        self.assertNotEqual(result.returncode,0);self.assertEqual(lib.load(self.root/lib.CATALOG)['entries'][0]['platform']['state'],'未投稿')

    def test_completed_metadata_is_locked_but_tags_remain_editable(self):
        e=self.fixture();self.complete(e);e['tags']=['新的检索标签']
        self.assertEqual(lib.integrity(self.root,e)['state'],'有效')
        e['description']='静默改变已交付介绍。'
        self.assertEqual(lib.integrity(self.root,e)['state'],'需复检')

    def test_draft_can_start_and_completed_cannot_revert(self):
        e=self.create(draft=True);self.assertEqual(e['status'],'设计草稿');lib.save(self.root/lib.CATALOG,self.data)
        command=[sys.executable,str(ROOT/'scripts/sticker_library.py'),'--root',str(self.root),'stage','--path',e['id'],'--state','制作中']
        result=subprocess.run(command,text=True,capture_output=True,timeout=20);self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(lib.load(self.root/lib.CATALOG)['entries'][0]['status'],'制作中')
        self.data=lib.load(self.root/lib.CATALOG);ready=self.fixture();self.complete(ready);lib.save(self.root/lib.CATALOG,self.data)
        result=subprocess.run([*command[:6],ready['id'],'--state','设计草稿'],text=True,capture_output=True,timeout=20)
        self.assertNotEqual(result.returncode,0);self.assertIn('已完成版本不能退回草稿',result.stderr)


if __name__=='__main__':unittest.main(verbosity=2)
