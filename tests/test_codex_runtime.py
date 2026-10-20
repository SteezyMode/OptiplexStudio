"""Canonical publisher package and additive repair regression coverage."""
import dataclasses
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import unittest
from unittest.mock import patch

import test_tool_installation as fixtures
n = fixtures.n
import codex_install as c


class CodexRuntime(unittest.TestCase):
    setUp = fixtures.Installation.setUp
    fixture = fixtures.Installation.fixture
    prepare = fixtures.Installation.prepare
    downloader = staticmethod(fixtures.Installation.downloader)

    def install(self, plan, data, **kw):
        with patch.object(n, '_download', side_effect=self.downloader(data)):
            return n.install({}, plan, consent=True, **kw)

    def legacy(self):
        plan, data = self.prepare('codex')
        old = plan.destination / 'codex'
        old.parent.mkdir(parents=True)
        old.write_bytes(b'fixture binary; never executed')
        old.chmod(0o700)
        (old.parent / 'installation.json').write_text(json.dumps({'version': plan.version}))
        return old, data

    def test_fresh_complete_packages_on_linux_and_macos(self):
        for system in ('Linux', 'Darwin'):
            for arch in ('x86_64', 'aarch64'):
                with self.subTest(system=system, arch=arch), patch.object(n.platform, 'system', return_value=system), patch.object(n.platform, 'machine', return_value=arch):
                    plan, data = self.prepare('codex', arch=arch)
                    path = self.install(plan, data)
                    self.assertEqual(n.discover({}, 'codex'), path)
                    self.assertEqual(n.inspect({}, 'codex')['status'], 'Components verified')
                    for name in c._required(plan.target):
                        self.assertTrue((plan.destination / name).is_file())
                    self.assertFalse(n.inspect({}, 'codex')['runtime_ready'])
                    import shutil
                    shutil.rmtree(plan.destination)

    def test_legacy_repair_pins_tag_and_preserves_every_existing_file(self):
        old, data = self.legacy()
        sentinels = [self.home / '.codex/auth.json', self.home / '.codex/config.toml',
                     self.home / 'StudioProjects/game/keep', old.parent / 'installation.json']
        for path in sentinels[:3]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('preserve exactly')
        before = {p: (p.read_bytes(), p.stat().st_ino) for p in [old, *sentinels]}
        config = {'codex_path': str(old), 'unknown_setting': 'keep'}
        self.assertEqual(n.inspect(config, 'codex')['status'], 'Repair needed')
        with patch.object(n, '_metadata', side_effect=self.metadata) as meta:
            plan = n.prepare_install(config, 'codex')
        self.assertTrue(all('/tags/rust-v0.163.0' in call.args[0] for call in meta.call_args_list))
        with patch.object(n, '_download', side_effect=self.downloader(data)):
            repaired = n.install(config, plan, consent=True)
        self.assertEqual(n.discover(config, 'codex'), repaired)
        self.assertEqual(Path(repaired).parent / 'codex-code-mode-host', plan.destination / 'bin/codex-code-mode-host')
        self.assertEqual(config, {'codex_path': str(old), 'unknown_setting': 'keep'})
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_ino) for p in before})
        self.assertEqual(n.inspect(config, 'codex')['status'], 'Components verified')
        with self.assertRaises(n.InstallError):
            n.prepare_install(config, 'codex')

    def test_canonical_repair_adds_only_missing_companions(self):
        plan, data = self.prepare('codex')
        path = Path(self.install(plan, data))
        inode = path.stat().st_ino
        host = path.parent / 'codex-code-mode-host'
        host.unlink()
        self.assertEqual(n.inspect({}, 'codex')['status'], 'Repair needed')
        repair = n.prepare_install({}, 'codex')
        self.install(repair, data)
        self.assertEqual(path.stat().st_ino, inode)
        self.assertTrue(host.is_file())
        self.assertEqual(n.inspect({}, 'codex')['status'], 'Components verified')

    def test_conflicting_companion_never_overwritten(self):
        plan, data = self.prepare('codex')
        path = Path(self.install(plan, data))
        host = path.parent / 'codex-code-mode-host'
        host.write_bytes(b'working binary from another version')
        repair = n.prepare_install({}, 'codex')
        with self.assertRaisesRegex(n.InstallError, 'conflicts'):
            self.install(repair, data)
        self.assertEqual(host.read_bytes(), b'working binary from another version')
        self.assertEqual(path.read_bytes(), b'fixture binary; never executed')

    def test_mismatched_retained_binary_fails_without_publishing(self):
        old, data = self.legacy()
        old.write_bytes(b'codex from another version')
        plan = n.prepare_install({}, 'codex')
        with self.assertRaisesRegex(n.InstallError, 'differs'):
            self.install(plan, data)
        self.assertFalse(plan.destination.exists())
        self.assertEqual(old.read_bytes(), b'codex from another version')

    def test_release_version_mismatch_and_missing_digest_fail_closed(self):
        old, data = self.legacy()
        _, release, metadata = self.fixture('codex')
        release['tag_name'] = 'rust-v0.164.0'
        with self.assertRaisesRegex(n.InstallError, 'version mismatch'):
            n.prepare_install({}, 'codex')
        release['tag_name'] = 'rust-v0.163.0'
        release['assets'][0]['digest'] = None
        with self.assertRaisesRegex(n.InstallError, 'SHA-256'):
            n.prepare_install({}, 'codex')

    def modified_package(self, transform):
        data, release, metadata = self.fixture('codex')
        source = io.BytesIO(data)
        output = io.BytesIO()
        with tarfile.open(fileobj=source, mode='r:gz') as inp, tarfile.open(fileobj=output, mode='w:gz') as out:
            for item in inp:
                body = inp.extractfile(item).read()
                body = transform(item.name, body)
                if body is None:
                    continue
                item.size = len(body)
                out.addfile(item, io.BytesIO(body))
        data = output.getvalue()
        release['assets'][0]['digest'] = 'sha256:' + hashlib.sha256(data).hexdigest()
        return n.prepare_install({}, 'codex'), data

    def test_package_manifest_version_and_target_must_match_release(self):
        for key, value in [('version', '0.162.0'), ('target', 'x86_64-apple-darwin'), ('entrypoint', '../codex')]:
            def change(name, body):
                if name == 'codex-package.json':
                    manifest = json.loads(body)
                    manifest[key] = value
                    return json.dumps(manifest).encode()
                return body
            plan, data = self.modified_package(change)
            with self.assertRaisesRegex(n.InstallError, 'mismatch'):
                self.install(plan, data)
            self.assertFalse(plan.destination.exists())

    def test_missing_companion_and_corrupt_archive_leave_no_install(self):
        plan, data = self.modified_package(lambda name, body: None if name.endswith('code-mode-host') else body)
        with self.assertRaisesRegex(n.InstallError, 'required runtime components'):
            self.install(plan, data)
        self.assertFalse(plan.destination.exists())
        with self.assertRaisesRegex(n.InstallError, 'Checksum mismatch'):
            self.install(plan, b'corrupt')
        self.assertFalse(plan.destination.exists())

    def test_publisher_metadata_changed_after_review(self):
        plan, data = self.prepare('codex')
        original = self.metadata
        def changed(url, **kw):
            release = json.loads(original(url, **kw))
            release['assets'][0]['digest'] = 'sha256:' + '0' * 64
            return json.dumps(release).encode()
        with patch.object(n, '_metadata', side_effect=changed), patch.object(n, '_download') as download:
            with self.assertRaisesRegex(n.InstallError, 'metadata changed'):
                n.install({}, plan, consent=True)
            download.assert_not_called()

    def test_external_executable_detected_without_automatic_execution_or_repair(self):
        path = self.home / 'custom/codex'
        path.parent.mkdir()
        path.write_bytes(b'custom')
        path.chmod(0o700)
        config = {'codex_path': str(path)}
        self.assertEqual(n.inspect(config, 'codex')['status'], 'Executable detected')
        with self.assertRaises(n.InstallError):
            n.prepare_install(config, 'codex')
        with patch.object(c.subprocess, 'run') as run:
            with self.assertRaises(n.InstallError):
                c.check_runtime(config)
            run.assert_not_called()

    def test_runtime_readiness_isolated_success_failure_timeout_and_version(self):
        plan, data = self.prepare('codex')
        self.install(plan, data)
        def run(argv, **kwargs):
            self.assertEqual(kwargs['env']['HOME'], kwargs['env']['CODEX_HOME'])
            self.assertNotEqual(kwargs['env']['HOME'], str(self.home))
            self.assertEqual(kwargs['cwd'], kwargs['env']['HOME'])
            self.assertEqual(kwargs['timeout'], 15)
            return subprocess.CompletedProcess(argv, 0, b'codex-cli 0.163.0\n')
        with patch.object(c.subprocess, 'run', side_effect=run) as mocked:
            result = c.check_runtime({})
            self.assertTrue(result['runtime_ready'])
            self.assertEqual(result['status'], 'Runtime checked')
            self.assertEqual(mocked.call_count, 4)
        for outcome in (subprocess.CompletedProcess([], 1, b''), subprocess.CompletedProcess([], 0, b'codex-cli 0.164.0'), subprocess.TimeoutExpired('codex', 15), OSError('wrong architecture')):
            with patch.object(c.subprocess, 'run', **({'side_effect': outcome} if isinstance(outcome, Exception) else {'return_value': outcome})):
                with self.assertRaises(n.InstallError):
                    c.check_runtime({})
        # A passive recheck never implies successful execution.
        self.assertFalse(n.inspect({}, 'codex')['runtime_ready'])

    def test_symlink_component_prevents_repair(self):
        old, data = self.legacy()
        plan = n.prepare_install({}, 'codex')
        plan.destination.mkdir()
        elsewhere = self.home / 'do-not-touch'
        elsewhere.write_text('keep')
        (plan.destination / 'bin').symlink_to(elsewhere.parent, target_is_directory=True)
        with self.assertRaisesRegex(n.InstallError, 'symbolic links'):
            self.install(plan, data)
        self.assertEqual(elsewhere.read_text(), 'keep')

    def test_standalone_distribution_repair_verified_against_same_release(self):
        old, package = self.legacy()
        old.write_bytes(b'publisher standalone signed binary')
        original_metadata = self.metadata
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w:gz') as archive:
            entry = tarfile.TarInfo('codex-x86_64-unknown-linux-musl')
            entry.size = old.stat().st_size
            archive.addfile(entry, io.BytesIO(old.read_bytes()))
        standalone = stream.getvalue()
        def metadata(url, **kw):
            release = json.loads(original_metadata(url, **kw))
            name = 'codex-x86_64-unknown-linux-musl.tar.gz'
            release['assets'].append(dict(name=name,
                browser_download_url='https://github.com/openai/codex/releases/download/rust-v0.163.0/' + name,
                digest='sha256:' + hashlib.sha256(standalone).hexdigest()))
            return json.dumps(release).encode()
        def download(url, output, *args):
            output.write(package if 'codex-package-' in url else standalone)
        with patch.object(n, '_metadata', side_effect=metadata), patch.object(n, '_download', side_effect=download):
            plan = n.prepare_install({}, 'codex')
            result = n.install({}, plan, consent=True)
        self.assertEqual(n.discover({'codex_path': str(old)}, 'codex'), result)
        self.assertEqual(old.read_bytes(), b'publisher standalone signed binary')
        self.assertEqual(n.inspect({}, 'codex')['status'], 'Components verified')

    def test_repair_cancellation_and_concurrency_preserve_existing_install(self):
        old, data = self.legacy()
        plan = n.prepare_install({}, 'codex')
        import threading
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(n.InstallCancelled):
            self.install(plan, data, cancel=cancel)
        self.assertFalse(plan.destination.exists())
        with (n.managed_root() / '.codex.lock').open('w') as lock:
            n.fcntl.flock(lock, n.fcntl.LOCK_EX | n.fcntl.LOCK_NB)
            with patch.object(n, '_download') as download:
                with self.assertRaisesRegex(n.InstallError, 'Another installation'):
                    n.install({}, plan, consent=True)
                download.assert_not_called()
        self.assertEqual(old.read_bytes(), b'fixture binary; never executed')
