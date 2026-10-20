import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import native_tools as native
import project_client


class NativeSetup(unittest.TestCase):
    def test_persistent_versioned_and_extracted_installs_without_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            examples = {'godot': 'godot-native/4.7.2/Godot_v4.7.2-stable_linux.x86_64',
                        'blender': 'blender-native/blender-5.2.0-linux-x64/blender',
                        'lmms': 'lmms-native/squashfs-root/AppRun',
                        'krita': 'krita-native/squashfs-root/AppRun'}
            with patch('native_tools.shutil.which', return_value=None), patch('native_tools.Path.home', return_value=root), patch('native_tools.subprocess.Popen', side_effect=AssertionError('No execution')):
                for name, relative in examples.items():
                    executable = root / relative
                    executable.parent.mkdir(parents=True, exist_ok=True)
                    executable.write_text('not run')
                    executable.chmod(0o700)
                    config = {'tool_dirs': [tmp]}
                    self.assertEqual(native.discover(config, name), str(executable))
                    self.assertEqual(native.inspect(config, name)['status'], 'Ready')

    def test_explicit_invalid_path_does_not_silently_fallback(self):
        with patch('native_tools.shutil.which') as which:
            result = native.inspect({'krita_path': '/missing/krita'}, 'krita')
            self.assertEqual(result['status'], 'Needs attention')
            which.assert_not_called()

    def test_path_and_local_bin_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp, patch('native_tools.shutil.which', return_value=None), patch('native_tools.Path.home', return_value=Path(tmp)), patch('native_tools.tool_roots', return_value=[]):
            self.assertEqual(native.inspect({}, 'codex')['status'], 'Missing')
            exe = Path(tmp) / '.local/bin/codex'
            exe.parent.mkdir(parents=True)
            exe.touch()
            exe.chmod(0o700)
            self.assertEqual(native.discover({}, 'codex'), str(exe))
        with patch('native_tools.shutil.which', return_value='/usr/bin/blockbench'):
            self.assertEqual(native.discover({}, 'blockbench'), '/usr/bin/blockbench')

    def test_vscodium_argv_and_project_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = {'projects_dir': tmp}
            project_client.request(config, 'code-project', 'create', template='Studio')
            with patch('native_tools.discover', return_value='/editor with spaces/codium'):
                args, cwd = native.command(config, 'vscodium', 'code-project')
                self.assertEqual(args, ['/editor with spaces/codium', '--', str(cwd)])
                with self.assertRaises(ValueError):
                    native.command(config, 'vscodium')
                with self.assertRaises(ValueError):
                    native.command(config, 'vscodium', '../escape')

    def test_invalid_roots(self):
        for roots in ('/tmp', ['relative'], [3]):
            with self.assertRaises(ValueError):
                native.tool_roots({'tool_dirs': roots})
