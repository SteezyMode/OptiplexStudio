"""Character Lab must never install or activate itself or touch existing work."""
import builtins
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import character_lab_setup as lab


class CharacterLabTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)

    def test_status_is_offline_and_non_mutating(self):
        with patch('character_lab_setup.subprocess.run', side_effect=AssertionError('No network or subprocess')):
            result = lab.describe(self.home)
            self.assertFalse(result['mpfb_server_prepared'])
            self.assertFalse(result['rigger_zip_prepared'])
            self.assertFalse(result['mpfb-mcp']['present'])
        self.assertFalse(lab.base_directory(self.home).exists())

    def test_checkout_refuses_symlinked_or_wrong_existing_source(self):
        root = lab.base_directory(self.home)
        root.mkdir(parents=True)
        outside = self.home / 'outside'
        outside.mkdir()
        (root / 'rigger').symlink_to(outside, target_is_directory=True)
        with patch('character_lab_setup.run', side_effect=AssertionError('No download')):
            with self.assertRaisesRegex(RuntimeError, 'not a directory'):
                lab.clone_pinned('rigger', root)
        (root / 'rigger').unlink()
        (root / 'rigger').mkdir()
        incorrect = subprocess.CompletedProcess(args=[], returncode=0, stdout='not-the-pinned-sha')
        with patch('character_lab_setup.subprocess.run', return_value=incorrect), \
             patch('character_lab_setup.run', side_effect=AssertionError('No download')):
            with self.assertRaisesRegex(RuntimeError, 'Different checkout'):
                lab.clone_pinned('rigger', root)

    def test_pinned_checkout_returns_existing_without_rewrite(self):
        root = lab.base_directory(self.home)
        checkout = root / 'mpfb-mcp'
        checkout.mkdir(parents=True)
        expected = lab.REPOS['mpfb-mcp'][1]
        with patch('character_lab_setup.subprocess.run',
                   return_value=subprocess.CompletedProcess([], 0, expected + '\n')) as process, \
             patch('character_lab_setup.run', side_effect=AssertionError('Do not update')):
            self.assertEqual(lab.clone_pinned('mpfb-mcp', root), checkout)
            process.assert_called_once()

    def test_prepared_tree_can_be_reused_without_subprocess(self):
        root = lab.base_directory(self.home)
        mpfb = root / 'mpfb-mcp'
        rigger = root / 'rigger'
        (mpfb / '.venv/bin').mkdir(parents=True)
        (mpfb / '.venv/bin/mpfb-mcp').touch()
        (rigger / 'dist').mkdir(parents=True)
        (rigger / 'dist/rigger-1.2.0.zip').touch()
        def existing(name, directory):
            return directory / name
        with patch('character_lab_setup.clone_pinned', side_effect=existing), \
             patch('character_lab_setup.run', side_effect=AssertionError('Already prepared')), \
             patch('character_lab_setup.venv.EnvBuilder', side_effect=AssertionError('Do not reinstall')):
            result = lab.prepare(self.home)
        self.assertEqual(result['rigger_zip'], str(rigger / 'dist/rigger-1.2.0.zip'))
        self.assertTrue(lab.describe(self.home)['rigger_zip_prepared'])

    def test_cli_requires_explicit_yes_before_any_work(self):
        for answer in ('', 'yes', 'YES please', 'n'):
            with self.subTest(answer=answer), \
                 patch.object(builtins, 'input', return_value=answer), \
                 patch('character_lab_setup.prepare', side_effect=AssertionError('Not approved')):
                self.assertEqual(lab.main(['prepare']), 1)
        with patch.object(builtins, 'input', return_value='YES'), \
             patch('character_lab_setup.prepare', return_value={}) as prepare:
            self.assertEqual(lab.main(['prepare']), 0)
            prepare.assert_called_once_with()

    def test_install_requires_both_tool_paths_before_any_work(self):
        with patch('character_lab_runtime.install', side_effect=AssertionError('No installation')):
            with self.assertRaises(SystemExit):
                lab.main(['install', '--yes'])

    def test_source_selection_is_immutable_and_pinned(self):
        for url, sha in lab.REPOS.values():
            self.assertTrue(url.startswith('https://github.com/'))
            self.assertEqual(len(sha), 40)
            self.assertTrue(all(c in '0123456789abcdef' for c in sha))


class CharacterLabUI(unittest.TestCase):
    def test_declining_setup_never_launches_anything(self):
        try:
            import tools_ui
        except ImportError:
            self.skipTest('GTK unavailable')
        host = MagicMock()
        host.window = None
        dialog = MagicMock()
        dialog.run.return_value = tools_ui.Gtk.ResponseType.NO
        with patch('native_tools.discover', side_effect=['/blender', '/codex']), \
             patch.object(tools_ui.Gtk, 'MessageDialog', return_value=dialog), \
             patch('tools_ui.subprocess.Popen', side_effect=AssertionError('Unexpected launch')):
            tools_ui.ToolsUI.prepare_character_lab(host)
        dialog.destroy.assert_called_once()

    def test_accepting_launches_only_a_local_terminal_helper(self):
        try:
            import tools_ui
        except ImportError:
            self.skipTest('GTK unavailable')
        host = MagicMock()
        host.window = None
        dialog = MagicMock()
        dialog.run.return_value = tools_ui.Gtk.ResponseType.YES
        with patch('native_tools.discover', side_effect=['/opt/blender 5/blender', '/opt/codex/bin/codex']), \
             patch.object(tools_ui.Gtk, 'MessageDialog', return_value=dialog), \
             patch('core.terminal_args', side_effect=lambda command: ['terminal', '--'] + command) as terminal, \
             patch('tools_ui.subprocess.Popen') as spawn:
            tools_ui.ToolsUI.prepare_character_lab(host)
        self.assertEqual(spawn.call_count, 1)
        self.assertIn('character_lab_setup.py', ' '.join(terminal.call_args.args[0]))
        self.assertIn('install', terminal.call_args.args[0])
        self.assertIn('--yes', terminal.call_args.args[0])
        self.assertIn('/opt/blender 5/blender', terminal.call_args.args[0])
        self.assertIn('/opt/codex/bin/codex', terminal.call_args.args[0])
        self.assertNotIn('sudo', str(spawn.call_args))


if __name__ == '__main__':
    unittest.main()
