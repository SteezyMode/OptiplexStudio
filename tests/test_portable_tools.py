"""Portable publisher fixtures and real shell execution; no downloaded code runs."""
import dataclasses
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import threading
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import native_tools as n
import portable_install as p
from tool_environment import ToolEnvironment


class Portable(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        for name, value in [('native_tools.Path.home', self.home),
                            ('native_tools.platform.system', 'Linux'),
                            ('native_tools.platform.machine', 'x86_64'),
                            ('native_tools.shutil.which', None)]:
            obj = patch(name, return_value=value)
            obj.start()
            self.addCleanup(obj.stop)
        roots = patch.object(n, 'tool_roots', side_effect=lambda _: [n.managed_root()])
        roots.start()
        self.addCleanup(roots.stop)

    def fixture(self, app, arch='x64'):
        version = '5.2.2' if app == 'blockbench' else '1.2.2' if app == 'lmms' else '1.100.123' if app == 'vscodium' else '5.2.6' if app == 'krita' else '4.5.1'
        if app in ('blockbench', 'lmms', 'krita'):
            body = b'\x7fELF' + b'\0'*4 + b'AI\x02' + b'fixture never executed'
        else:
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode='w:gz') as tar:
                names = ['bin/codium', 'resources/app.txt'] if app == 'vscodium' else ['blender-'+version+'-linux-'+arch+'/blender', 'blender-'+version+'-linux-'+arch+'/lib/library.so']
                for name in names:
                    info = tarfile.TarInfo(name)
                    info.mode, info.size = 0o755, 7
                    tar.addfile(info, io.BytesIO(b'fixture'))
            body = stream.getvalue()
        digest = hashlib.sha256(body).hexdigest()
        asset = ('Blockbench_'+version+'.AppImage' if app == 'blockbench' else
                 'lmms-'+version+'-linux-x86_64.AppImage' if app == 'lmms' else
                 'VSCodium-linux-'+arch+'-'+version+'.tar.gz' if app == 'vscodium' else
                 'krita-'+version+'-x86_64.appimage' if app == 'krita' else
                 'blender-'+version+'-linux-'+arch+'.tar.xz')
        repo = p.REPOS.get(app)
        prefix = 'https://github.com/'+repo+'/releases/download/'+version+'/' if repo else ''
        release = dict(tag_name=version, assets=[dict(name=asset, browser_download_url=prefix+asset, digest='sha256:'+digest)])
        def metadata(url, **kwargs):
            if url.endswith('/latest'):
                return json.dumps(release).encode()
            if url == n.PUBLISHERS['blender']:
                return ('blender-'+version+'-linux-x64.tar.xz').encode()
            if url == n.PUBLISHERS['krita']:
                return ('https://download.kde.org/stable/krita/'+version+'/'+asset).encode()
            if url.endswith('.mirrorlist'):
                return ('<b>SHA-256:</b> '+digest).encode()
            return (digest+'  '+asset+'\n').encode()
        return body, release, metadata

    def install_fixture(self, app, config=None, arch='x64'):
        config = config or {}
        body, release, metadata = self.fixture(app, arch)
        with patch.object(n, '_metadata', side_effect=metadata):
            plan = n.prepare_install(config, app)
            with patch.object(n, '_download', side_effect=lambda url, out, *args: out.write(body)), patch.object(n.subprocess, 'Popen', side_effect=AssertionError('No execution allowed')):
                path = n.install(config, plan, consent=True)
        return Path(path), plan

    def test_all_publishers_install_discover_and_preserve(self):
        for app in n.OPTIONAL:
            with self.subTest(app=app):
                path, plan = self.install_fixture(app)
                self.assertEqual(n.discover({}, app), str(path))
                self.assertEqual(n.inspect({}, app)['status'], 'Ready')
                with self.assertRaises(n.InstallError):
                    n.prepare_install({}, app)
                self.assertTrue((plan.destination/p.RECEIPT).is_file())

    def test_arm64_archives_and_appimage_guidance(self):
        with patch.object(n.platform, 'machine', return_value='aarch64'):
            for app in ('blender', 'vscodium'):
                path, _ = self.install_fixture(app, arch='arm64')
                self.assertTrue(path.is_file())
            for app in ('krita', 'blockbench', 'lmms'):
                with self.assertRaisesRegex(n.InstallError, 'ARM64'):
                    n.prepare_install({}, app)

    def test_additive_repair_keeps_override_and_old_payload(self):
        path, plan = self.install_fixture('blender')
        old = path.read_bytes()
        config = {'blender_path': str(path), 'unrelated': 'preserved'}
        path.write_bytes(b'damaged')
        self.assertTrue(n.inspect(config, 'blender')['repairable'])
        repaired, new = self.install_fixture('blender', config)
        self.assertNotEqual(new.destination, plan.destination)
        self.assertEqual(path.read_bytes(), b'damaged')
        self.assertEqual(repaired.read_bytes(), old)
        self.assertEqual(n.discover(config, 'blender'), str(repaired))
        self.assertEqual(config['blender_path'], str(path))

    def test_consent_checksum_cancel_and_cleanup(self):
        body, _, metadata = self.fixture('blockbench')
        with patch.object(n, '_metadata', side_effect=metadata):
            plan = n.prepare_install({}, 'blockbench')
            with self.assertRaises(n.InstallError):
                n.install({}, plan)
            with patch.object(n, '_download', side_effect=lambda url, out, *args: out.write(b'wrong')):
                with self.assertRaisesRegex(n.InstallError, 'Checksum mismatch'):
                    n.install({}, plan, consent=True)
            event = threading.Event()
            def download(url, out, *args):
                out.write(body)
                event.set()
            with patch.object(n, '_download', side_effect=download):
                with self.assertRaises(n.InstallCancelled):
                    n.install({}, plan, consent=True, cancel=event)
            self.assertFalse(plan.destination.exists())
            self.assertFalse(list(n.managed_root().glob('.install-*')))

    def test_untrusted_metadata_and_plan_changes(self):
        body, release, metadata = self.fixture('blockbench')
        with patch.object(n, '_metadata', side_effect=metadata):
            plan = n.prepare_install({}, 'blockbench')
            for change in (dict(url='https://evil.example/tool'), dict(destination=self.home/'project'), dict(checksum='a'*64)):
                with self.assertRaises(n.InstallError):
                    n.install({}, dataclasses.replace(plan, **change), consent=True)
            release['assets'][0]['digest'] = None
            with self.assertRaisesRegex(n.InstallError, 'SHA-256'):
                n.prepare_install({}, 'blockbench')

    def test_unsafe_tar_entries_and_links(self):
        for name, kind, link in [('../escape', tarfile.REGTYPE, ''), ('/absolute', tarfile.REGTYPE, ''), ('special',tarfile.FIFOTYPE,''), ('link',tarfile.SYMTYPE,'/etc/passwd'), ('link',tarfile.SYMTYPE,'../../escape'), ('link',tarfile.SYMTYPE,'link')]:
            with self.subTest(name=name, link=link):
                archive = self.home/'archive.tar'
                with tarfile.open(archive,'w') as tar:
                    item = tarfile.TarInfo(name)
                    item.type, item.linkname = kind, link
                    tar.addfile(item)
                with tempfile.TemporaryDirectory(dir=self.home) as out, self.assertRaises(n.InstallError):
                    p.extract(archive, Path(out), None)

    def test_manual_managed_layout_and_raw_appimage_remain_discoverable(self):
        for app, name in [('blender', '4.5/blender'), ('blockbench', '5.2/Blockbench_5.2.AppImage')]:
            binary = n.managed_root() / app / name
            binary.parent.mkdir(parents=True)
            binary.write_text('manual install')
            binary.chmod(0o700)
            self.assertEqual(n.discover({}, app), str(binary))
            with self.assertRaises(n.InstallError):
                n.prepare_install({}, app)

    def test_bad_appimage_is_not_published(self):
        body, _, metadata = self.fixture('blockbench')
        with patch.object(n, '_metadata', side_effect=metadata):
            plan = n.prepare_install({}, 'blockbench')
            with patch.object(n, '_download', side_effect=lambda url, out, *args: out.write(body)), patch.object(p.shutil, 'copyfile', side_effect=AssertionError('Not reached')):
                # A valid publisher checksum of a non-AppImage still fails format checks.
                bad = b'not an AppImage'
                plan = dataclasses.replace(plan, checksum=hashlib.sha256(bad).hexdigest())
                with patch.object(p, 'prepare', return_value=plan), patch.object(n, '_download', side_effect=lambda url, out, *args: out.write(bad)):
                    with self.assertRaisesRegex(n.InstallError, 'AppImage format'):
                        n.install({}, plan, consent=True)
                self.assertFalse(plan.destination.exists())

    def test_managed_ancestor_symlink_rejected(self):
        body, _, metadata = self.fixture('blockbench')
        with patch.object(n, '_metadata', side_effect=metadata):
            plan = n.prepare_install({}, 'blockbench')
            root = n.managed_root()
            root.parent.mkdir(parents=True)
            outside = self.home / 'outside'
            outside.mkdir()
            root.symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(n.InstallError, 'symbolic links'):
                n.install({}, plan, consent=True)
            self.assertFalse(list(outside.iterdir()))

    def test_internal_links_are_copied_without_privileged_modes(self):
        archive = self.home/'archive.tar'
        with tarfile.open(archive,'w') as tar:
            item = tarfile.TarInfo('bin/tool')
            item.mode, item.size = 0o6755, 4
            tar.addfile(item, io.BytesIO(b'tool'))
            link = tarfile.TarInfo('bin/alias')
            link.type, link.linkname = tarfile.SYMTYPE, 'chain'
            tar.addfile(link)
            chain = tarfile.TarInfo('bin/chain')
            chain.type, chain.linkname = tarfile.SYMTYPE, 'tool'
            tar.addfile(chain)
        output = self.home/'out'
        output.mkdir()
        p.extract(archive, output, None)
        self.assertFalse((output/'bin/alias').is_symlink())
        self.assertEqual((output/'bin/alias').read_bytes(),b'tool')
        self.assertEqual((output/'bin/tool').stat().st_mode & 0o7777,0o700)

    def test_link_copy_expansion_is_bounded(self):
        archive = self.home/'archive.tar'
        with tarfile.open(archive, 'w') as tar:
            item = tarfile.TarInfo('tool')
            item.mode, item.size = 0o755, 4
            tar.addfile(item, io.BytesIO(b'tool'))
            link = tarfile.TarInfo('alias')
            link.type, link.linkname = tarfile.SYMTYPE, 'tool'
            tar.addfile(link)
        output = self.home/'output'
        output.mkdir()
        with patch.object(p, 'MAX_UNPACKED', 4), self.assertRaisesRegex(n.InstallError, 'links exceed'):
            p.extract(archive, output, None)


class ShellTools(unittest.TestCase):
    def test_aliases_quote_paths_and_keep_headless_writes_in_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cwd = root/'project'
            cwd.mkdir()
            binary = root/"Godot's binary"
            binary.write_text('#!/bin/sh\nprintf "%s\\n" "$XDG_DATA_HOME" "$@"\n')
            binary.chmod(0o700)
            def discover(config, app):
                if app == 'godot': return str(binary)
                raise RuntimeError('missing')
            with patch.object(n, 'discover', side_effect=discover):
                tools = ToolEnvironment({}, cwd)
            self.addCleanup(tools.close)
            env = dict(os.environ, PATH=tools.path)
            result = subprocess.run(['/bin/bash','-c','godot4 --headless --path "$PWD"'], cwd=cwd,env=env,capture_output=True,text=True,check=True)
            self.assertEqual(result.stdout.splitlines(),[str(cwd/'.studio/headless/data'),'--headless','--path',str(cwd)])
            self.assertFalse(tools.config()['allow_login_shell'])
            self.assertEqual(tools.config()['shell_environment_policy']['set']['PATH'],tools.path)
            self.assertFalse(Path(tools.directory.name).is_relative_to(cwd))

    def test_managed_godot_versioned_discovery(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(n.Path,'home',return_value=Path(directory)), patch.object(n.shutil,'which',return_value=None):
            binary=n.managed_root()/'godot/4.7.2-stable/Godot_v4.7.2-stable_linux.x86_64'
            binary.parent.mkdir(parents=True)
            binary.write_text('fixture')
            binary.chmod(0o700)
            self.assertEqual(n.discover({},'godot'),str(binary))

    def test_verified_codex_companion_path_is_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            cwd = Path(directory)
            def discover(config, app):
                if app == 'codex': return '/managed/codex/version/bin/codex'
                raise RuntimeError('missing')
            with patch.object(n, 'discover', side_effect=discover), patch('codex_install.inspect_runtime', return_value={'status': 'Components verified'}):
                tools = ToolEnvironment({}, cwd)
            self.addCleanup(tools.close)
            self.assertIn('/managed/codex/version/codex-path', tools.path.split(os.pathsep))

    def test_aliases_never_live_in_project_even_when_tmpdir_is_project(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, TMPDIR=directory), patch.object(n, 'discover', side_effect=RuntimeError('missing')):
            tools = ToolEnvironment({}, Path(directory))
            try:
                self.assertFalse(Path(tools.directory.name).resolve().is_relative_to(Path(directory).resolve()))
            finally:
                tools.close()
        with self.assertRaisesRegex(ValueError, 'outside the selected Project'):
            ToolEnvironment({}, Path('/tmp'))
