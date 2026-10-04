"""Public build and restoration tests use synthetic, isolated library fixtures."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

import publish_library as pub
import sticker_library as lib
import test_sticker_library as fixtures


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.LibraryTests('test_alias_and_monotonic_versions')
        self.fixture.setUp(); self.root = self.fixture.root
        entry = self.fixture.fixture(); self.fixture.complete(entry)
        lib.refresh(self.root, self.fixture.data, self.fixture.config)
        lib.save(self.root / 'deployment/config.json', {'repository': 'example/test-library',
            'domain': 'stickers.example.com', 'public_url': 'https://stickers.example.com/', 'release_tag': 'materials-v1'})
        for path in ('作品库设计与规则.md', 'AGENTS.md', '00_官方调研/微信表情制作与投稿调研.md', 'deployment/部署与更新.md'):
            lib.save(self.root / path, '# 隔离测试\n\n仅用于测试，不是实际发布资料。')
        pub.prepare(self.root)

    def tearDown(self):
        self.fixture.tearDown()

    def test_character_materials_publish_images_and_same_domain_zip(self):
        material = self.fixture.material_fixture()
        lib.refresh(self.root, self.fixture.data, self.fixture.config)
        pub.prepare(self.root)
        site = self.root / '_site'; pub.build(self.root, site)
        catalog = lib.load(site / 'catalog.json')
        published = catalog['materials'][0]
        self.assertEqual(published['id'], material['id'])
        self.assertEqual(lib.sha(site / published['assets'][0]['path']), material['assets'][0]['sha256'])
        self.assertTrue((site / published['packages'][0]['path']).is_file())
        self.assertTrue((site / published['preview']).is_file())
        self.assertTrue((site / published['copy']).is_file())

    def test_public_links_and_release_downloads(self):
        site = self.root / '_site'; result = pub.build(self.root, site)
        self.assertEqual(result['versions'], 1); self.assertEqual(result['stickers'], 8)
        self.assertEqual([p.name for p in site.rglob('*.zip')], ['submission_PNG.zip'])
        data = lib.load(site / 'catalog.json')
        packages = data['entries'][0]['packages']
        self.assertEqual(result['site_downloads'], 1); self.assertEqual(result['release_downloads'], 1)
        for package in packages:
            if package['path'].endswith('submission_PNG.zip'):
                self.assertTrue((site / package['path']).is_file())
                self.assertEqual(lib.sha(site / package['path']), package['sha256'])
            else:
                self.assertTrue(package['path'].startswith('https://github.com/example/test-library/releases/download/'))
        self.assertEqual(data['entries'][0]['completion']['gate']['profile_date'], '2026-10-02')
        for page in site.rglob('*.html'):
            links = pub.Links(); links.feed(page.read_text())
            for url in links.values:
                if urlsplit(url).scheme or url.startswith('#'):continue
                target = (page.parent / unquote(url.split('#')[0])).resolve()
                self.assertTrue(target.is_relative_to(site), url)
                self.assertTrue(target.is_file(), url)

    def test_publishing_keeps_original_bytes_and_timestamps(self):
        entry = self.fixture.data['entries'][0]
        originals = {str(p): (lib.sha(p), p.stat().st_mtime_ns) for p in lib.protected_files(self.root / entry['path'])}
        pub.build(self.root, self.root / '_site')
        self.assertEqual(originals, {str(p): (lib.sha(p), p.stat().st_mtime_ns) for p in lib.protected_files(self.root / entry['path'])})

    def test_draft_packages_and_preview_are_not_published(self):
        draft = self.fixture.fixture()
        out = self.root / draft['path'] / '04_成品'
        (out / 'preview.html').write_text('<a href="submission_PNG.zip">未验收包</a>')
        unrelated = self.root / '未登记.zip'
        shutil.copy2(out / 'submission_PNG.zip', unrelated)
        before = {p.name: lib.sha(p) for p in out.glob('*.zip')}
        lib.refresh(self.root, self.fixture.data, self.fixture.config)
        pub.prepare(self.root)
        records = lib.load(self.root / 'deployment/archives.json')
        paths = [p for asset in records['assets'] for p in asset['paths']]
        self.assertFalse(any(p.startswith(draft['path'] + '/') for p in paths))
        self.assertNotIn(unrelated.name, paths)
        site = self.root / '_site'; result = pub.build(self.root, site)
        self.assertEqual(result['versions'], 2)
        public = next(e for e in lib.load(site / 'catalog.json')['entries'] if e['id'] == draft['id'])
        self.assertFalse(public['can_download'])
        self.assertEqual(public['status'], '制作中')
        self.assertEqual(public['packages'], [])
        self.assertIsNone(public['preview'])
        self.assertFalse((site / draft['path'] / '04_成品/preview.html').exists())
        self.assertFalse(list((site / draft['path']).rglob('*.zip')))
        self.assertEqual(before, {p.name: lib.sha(p) for p in out.glob('*.zip')})

    def test_restore_missing_alias_and_preserve_changed_existing_zip(self):
        entry = self.fixture.data['entries'][0]
        original = self.root / entry['path'] / '04_成品/submission_PNG.zip'
        alias = self.root / '02_上传包/隔离测试.zip'; alias.parent.mkdir(); shutil.copy2(original, alias)
        pub.prepare(self.root); original.unlink()
        self.assertEqual(pub.restore(self.root)['restored_paths'], 1)
        self.assertEqual(lib.sha(original), lib.sha(alias))
        original.write_bytes(original.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'preserving'):
            pub.restore(self.root)

    def test_failed_build_preserves_previous_site_and_refuses_source_output(self):
        site = self.root / '_site'; pub.build(self.root, site); before = (site / 'index.html').read_bytes()
        records = lib.load(self.root / 'deployment/archives.json'); records['assets'] = []; lib.save(self.root / 'deployment/archives.json', records)
        with self.assertRaisesRegex(ValueError, 'prepared'):
            pub.build(self.root, site)
        self.assertEqual((site / 'index.html').read_bytes(), before)
        for output in (self.root, self.root / self.fixture.data['entries'][0]['path'], self.root / 'scripts'):
            with self.assertRaises(ValueError):pub.build(self.root, output)

    def test_branch_publish_preserves_source_index_and_history_and_rejects_stale_build(self):
        def git(*args):
            return subprocess.check_output(['git', *args], cwd=self.root, text=True, stderr=subprocess.DEVNULL).strip()
        remote = self.root / 'remote.git'
        git('init', '-q', '--bare', str(remote)); git('init', '-q', '-b', 'main')
        git('config', 'user.name', 'Isolated test'); git('config', 'user.email', 'test@example.invalid')
        (self.root / '.gitignore').write_text('/_site/\n/remote.git/\n/deployment/staging/\n')
        git('add', '--all'); git('commit', '-qm', 'Synthetic test only'); git('remote', 'add', 'origin', str(remote))
        source = git('rev-parse', 'HEAD'); index = lib.sha(self.root / '.git/index')
        site = self.root / '_site'
        with patch.dict(os.environ, {'GITHUB_SHA': source}):pub.build(self.root, site)
        first = pub.push_site(self.root, site); second = pub.push_site(self.root, site)
        self.assertEqual(git('rev-parse', 'HEAD'), source)
        self.assertEqual(lib.sha(self.root / '.git/index'), index)
        self.assertEqual(git('status', '--porcelain'), '')
        self.assertEqual(git('rev-parse', second['pages_commit'] + '^'), first['pages_commit'])
        self.assertEqual(git('show', second['pages_commit'] + ':CNAME'), 'stickers.example.com')
        self.assertNotIn('scripts/', git('ls-tree', '-r', '--name-only', second['pages_commit']))
        (self.root / 'new-source.txt').write_text('Changed source')
        with self.assertRaisesRegex(ValueError, 'Commit source'):pub.push_site(self.root, site)
        git('add', 'new-source.txt'); git('commit', '-qm', 'Update synthetic source')
        with self.assertRaisesRegex(ValueError, 'does not match'):pub.push_site(self.root, site)


if __name__ == '__main__':unittest.main(verbosity=2)
