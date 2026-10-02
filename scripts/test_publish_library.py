"""Public build and restoration tests use synthetic, isolated library fixtures."""
import json
from pathlib import Path
import shutil
import unittest
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

    def test_public_links_and_release_downloads(self):
        site = self.root / '_site'; result = pub.build(self.root, site)
        self.assertEqual(result['versions'], 1); self.assertEqual(result['stickers'], 8)
        self.assertEqual(list(site.rglob('*.zip')), [])
        data = lib.load(site / 'catalog.json')
        self.assertTrue(all(p['path'].startswith('https://github.com/example/test-library/releases/download/')
                            for e in data['entries'] for p in e['packages']))
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


if __name__ == '__main__':unittest.main(verbosity=2)
