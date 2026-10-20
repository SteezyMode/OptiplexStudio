"""Offline publisher fixtures; no real installs, credentials, or projects."""
import dataclasses
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import threading
import unittest
from unittest.mock import patch
import zipfile
import warnings

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import native_tools as n


class Installation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        for target, value in [('native_tools.Path.home', self.home),
                              ('native_tools.shutil.which', None),
                              ('native_tools.platform.system', 'Linux'),
                              ('native_tools.platform.machine', 'x86_64')]:
            patcher = patch(target, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        roots = patch.object(n, 'tool_roots', side_effect=lambda config: [n.managed_root()])
        roots.start()
        self.addCleanup(roots.stop)
        self.metadata = None
        metadata_patch = patch.object(n, '_metadata', side_effect=lambda url, **kw: self.metadata(url, **kw))
        metadata_patch.start()
        self.addCleanup(metadata_patch.stop)
        self.no_exec = patch('native_tools.subprocess.Popen', side_effect=AssertionError('Installer must not execute'))
        self.no_exec.start()
        self.addCleanup(self.no_exec.stop)

    def fixture(self, app='godot', arch='x86_64', unsafe=False):
        version = '4.7.2-stable' if app == 'godot' else 'rust-v0.163.0'
        member = ('Godot_v' + version + '_linux.' + ('arm64' if arch == 'aarch64' else arch)
                  if app == 'godot' else 'codex-' + arch + '-unknown-linux-musl')
        stream = io.BytesIO()
        if app == 'godot':
            with zipfile.ZipFile(stream, 'w') as z:
                if unsafe:
                    entry = zipfile.ZipInfo(member)
                    entry.external_attr = 0o120777 << 16
                    z.writestr(entry, '/tmp/target')
                else:
                    z.writestr(member, b'fixture binary; never executed')
                z.writestr('../outside', b'never extract this')
            algorithm, suffix = 'sha512', '.zip'
        else:
            with tarfile.open(fileobj=stream, mode='w:gz') as t:
                member = 'bin/codex'
                entry = tarfile.TarInfo(member)
                if unsafe:
                    entry.type = tarfile.SYMTYPE
                    entry.linkname = '/tmp/target'
                    t.addfile(entry)
                else:
                    data = b'fixture binary; never executed'
                    entry.size = len(data)
                    t.addfile(entry, io.BytesIO(data))
                import codex_install as c
                target = arch + ('-apple-darwin' if n.platform.system() == 'Darwin' else '-unknown-linux-musl')
                manifest = dict(layoutVersion=1, version='0.163.0', target=target, variant='codex', entrypoint='bin/codex', resourcesDir='codex-resources', pathDir='codex-path')
                for name in c._required(target)[1:]:
                    body = json.dumps(manifest).encode() if name.endswith('.json') else b'companion fixture'
                    item = tarfile.TarInfo(name)
                    item.size = len(body)
                    t.addfile(item, io.BytesIO(body))
            algorithm, suffix = 'sha256', '.tar.gz'
        archive = stream.getvalue()
        asset = member + suffix if app == 'godot' else 'codex-package-' + target + '.tar.gz'
        prefix = 'https://github.com/' + n.REPOSITORIES[app] + '/releases/download/' + version + '/'
        checksum = hashlib.new(algorithm, archive).hexdigest()
        release = dict(tag_name=version, draft=False, prerelease=False, assets=[
            dict(name=asset, browser_download_url=prefix + asset, digest='sha256:' + checksum)])
        if app == 'godot':
            release['assets'].append(dict(name='SHA512-SUMS.txt', browser_download_url=prefix + 'SHA512-SUMS.txt'))
        def metadata(url, **kwargs):
            if url.endswith('/latest') or '/tags/' in url:
                return json.dumps(release).encode()
            self.assertEqual(url, prefix + 'SHA512-SUMS.txt')
            return (checksum + '  ' + asset + '\n').encode()
        self.metadata = metadata
        return archive, release, metadata

    def prepare(self, app='godot', **kwargs):
        archive, release, metadata = self.fixture(app, **kwargs)
        with patch.object(n, '_metadata', side_effect=metadata):
            plan = n.prepare_install({}, app)
        return plan, archive

    @staticmethod
    def downloader(data):
        def download(url, output, limit, progress, cancel):
            n._check_cancel(cancel)
            output.write(data)
            progress('Downloading', len(data), len(data))
        return download

    def test_verified_install_and_discovery_both_architectures(self):
        for app in ('godot', 'codex'):
            for arch in ('x86_64', 'aarch64'):
                with self.subTest(app=app, arch=arch), patch.object(n.platform, 'machine', return_value=arch):
                    plan, data = self.prepare(app, arch=arch)
                    events = []
                    config = {'unrelated': 'preserved'}
                    with patch.object(n, '_download', side_effect=self.downloader(data)):
                        path = n.install(config, plan, consent=True, progress=lambda *a: events.append(a))
                    self.assertEqual(n.discover(config, app), path)
                    self.assertEqual(config, {'unrelated': 'preserved'})
                    self.assertEqual(Path(path).read_bytes(), b'fixture binary; never executed')
                    self.assertTrue(os.access(path, os.X_OK))
                    self.assertEqual(json.loads((plan.destination / ('studio-runtime.json' if app == 'codex' else 'installation.json')).read_text())['checksum'], plan.checksum)
                    self.assertGreaterEqual(len(events), 4)
                    self.assertFalse((plan.destination.parent / 'outside').exists())
                    # Isolate the next architecture fixture without touching a user install.
                    import shutil
                    shutil.rmtree(plan.destination)

    def test_consent_required_before_any_files_or_network(self):
        plan, _ = self.prepare()
        with patch.object(n, '_download') as download:
            for consent in (False, None, 1, 'yes'):
                with self.assertRaises(n.InstallError):
                    n.install({}, plan, consent=consent)
            download.assert_not_called()
        self.assertFalse(n.managed_root().exists())

    def test_checksum_failure_cleanup_then_retry(self):
        plan, data = self.prepare()
        with patch.object(n, '_download', side_effect=self.downloader(b'tampered')):
            with self.assertRaisesRegex(n.InstallError, 'Checksum mismatch'):
                n.install({}, plan, consent=True)
        self.assertFalse(plan.destination.exists())
        self.assertEqual(list(n.managed_root().glob('.install-*')), [])
        with patch.object(n, '_download', side_effect=self.downloader(data)):
            n.install({}, plan, consent=True)

    def test_cancellation_and_interrupted_download_cleaned(self):
        plan, _ = self.prepare()
        event = threading.Event()
        event.set()
        with self.assertRaises(n.InstallCancelled):
            n.install({}, plan, consent=True, cancel=event)
        def fail(url, output, *args):
            output.write(b'partial')
            raise OSError('network interrupted')
        with patch.object(n, '_download', side_effect=fail), self.assertRaises(OSError):
            n.install({}, plan, consent=True)
        self.assertFalse(plan.destination.exists())
        self.assertEqual(list(n.managed_root().glob('.install-*')), [])

    def test_symlink_archive_member_rejected(self):
        for app in ('godot', 'codex'):
            plan, data = self.prepare(app, unsafe=True)
            with patch.object(n, '_download', side_effect=self.downloader(data)):
                with self.assertRaisesRegex(n.InstallError, 'regular executable|Unsafe'):
                    n.install({}, plan, consent=True)
            self.assertFalse(plan.destination.exists())

    def test_existing_or_invalid_configuration_never_downloads(self):
        plan, _ = self.prepare()
        exe = self.home / 'existing'
        exe.touch()
        exe.chmod(0o700)
        for config in ({'godot_path': str(exe)}, {'godot_path': '/missing/executable'}):
            with patch.object(n, '_metadata') as metadata, patch.object(n, '_download') as download:
                with self.assertRaises(n.InstallError):
                    n.prepare_install(config, 'godot')
                with self.assertRaises(n.InstallError):
                    n.install(config, plan, consent=True)
                metadata.assert_not_called()
                download.assert_not_called()
        plan.destination.mkdir(parents=True)
        sentinel = plan.destination / 'keep'
        sentinel.write_text('keep')
        with self.assertRaises(n.InstallError):
            n.install({}, plan, consent=True)
        self.assertEqual(sentinel.read_text(), 'keep')

    def test_missing_integrity_or_unexpected_url_fails_closed(self):
        for app in ('godot', 'codex'):
            _, release, metadata = self.fixture(app)
            if app == 'codex':
                release['assets'][0].pop('digest')
            else:
                release['assets'].pop()
            with patch.object(n, '_metadata', side_effect=metadata):
                with self.assertRaises(n.InstallError):
                    n.prepare_install({}, app)
        _, release, metadata = self.fixture()
        release['assets'][0]['browser_download_url'] = 'https://evil.example/download'
        with patch.object(n, '_metadata', side_effect=metadata), self.assertRaises(n.InstallError):
            n.prepare_install({}, 'godot')

    def test_unsupported_architecture_guidance(self):
        with patch.object(n.platform, 'machine', return_value='riscv64'):
            for tool in n.INSTALLERS:
                with self.assertRaisesRegex(n.InstallError, 'architecture|ARM64'):
                    n.prepare_install({}, tool)

    def test_changed_plan_and_managed_symlinks_rejected(self):
        plan, _ = self.prepare()
        for changed in (dataclasses.replace(plan, version='../escape'),
                        dataclasses.replace(plan, url='https://evil.example/file'),
                        dataclasses.replace(plan, destination=self.home / 'project'),
                        dataclasses.replace(plan, algorithm='md5')):
            with self.assertRaises(n.InstallError):
                n.install({}, changed, consent=True)
        self.assertFalse(n.managed_root().exists())
        other = self.home / 'unrelated'
        other.mkdir()
        n.managed_root().parent.mkdir(parents=True)
        n.managed_root().symlink_to(other, target_is_directory=True)
        with self.assertRaisesRegex(n.InstallError, 'symbolic links'):
            n.install({}, plan, consent=True)
        self.assertEqual(list(other.iterdir()), [])

    def test_concurrent_install_fails_without_download(self):
        plan, _ = self.prepare()
        n.managed_root().mkdir(parents=True)
        with (n.managed_root() / '.godot.lock').open('w') as lock:
            n.fcntl.flock(lock, n.fcntl.LOCK_EX | n.fcntl.LOCK_NB)
            with patch.object(n, '_download') as download:
                with self.assertRaisesRegex(n.InstallError, 'Another installation'):
                    n.install({}, plan, consent=True)
                download.assert_not_called()

    def test_redirect_trust_boundary(self):
        for url in ('http://github.com/a', 'https://evil.example/a',
                    'https://github.com.evil.example/a', 'https://user@github.com/a',
                    'https://github.com:444/a', 'file:///tmp/a'):
            with self.assertRaises(n.InstallError):
                n._trusted_url(url)
        redirect = n._ReleaseRedirect()
        from urllib.request import Request
        with self.assertRaises(n.InstallError):
            redirect.redirect_request(Request('https://github.com/file'), None, 302, '', {}, 'https://evil.example/a')

    def test_download_limits_and_incomplete_response(self):
        class Response(io.BytesIO):
            def geturl(self): return 'https://github.com/official/file'
        for data, length, limit in [(b'ab', '3', 10), (b'ab', '20', 10), (b'123456', None, 5)]:
            response = Response(data)
            response.headers = {'Content-Length': length} if length else {}
            with patch.object(n.urllib.request, 'build_opener') as opener:
                opener.return_value.open.return_value = response
                with self.assertRaises(n.InstallError):
                    n._download('https://github.com/official/file', io.BytesIO(), limit, lambda *a: None, None)

    def test_duplicate_or_missing_archive_member(self):
        plan, _ = self.prepare()
        for names in ([plan.member, plan.member], ['../' + plan.member]):
            data = io.BytesIO()
            with warnings.catch_warnings(), zipfile.ZipFile(data, 'w') as z:
                warnings.simplefilter('ignore', UserWarning)
                for name in names:
                    z.writestr(name, b'fixture')
            archive = self.home / 'archive.zip'
            archive.write_bytes(data.getvalue())
            with self.assertRaises(n.InstallError):
                n._extract_binary(archive, plan, self.home / 'output', None)
