"""Regression checks for unified Studio projects and Codex authorization."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import project_helper
import native_tools


class UnifiedProject(unittest.TestCase):
    def test_single_project_format_with_multiple_tool_directories(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project_helper.create_project(root, 'sandbox')
            folder = root / 'sandbox'
            self.assertEqual(json.loads((folder / 'studio-project.json').read_text()),
                             {'version': 2, 'type': 'Studio', 'engine': 'godot'})
            self.assertTrue((folder / 'project.godot').is_file())
            for directory in ('docs', 'scenes', 'scripts', 'music', 'art', 'models',
                              'assets/audio/music', 'assets/3d'):
                self.assertTrue((folder / directory).is_dir())
            project = project_helper.Project(root, 'sandbox')
            try:
                self.assertEqual(project.project_type(), 'Studio')
                self.assertEqual(project.ensure_docs(), [])
            finally:
                project.close()
            with self.assertRaisesRegex(ValueError, 'Unsupported project template'):
                project_helper.create_project(root, 'old', 'Blank')

    def test_codex_login_status_is_read_only_and_not_live_readiness(self):
        with patch('native_tools.discover', return_value='/codex'), \
             patch('native_tools.subprocess.run') as check:
            check.return_value = MagicMock(returncode=0, stdout='Logged in using ChatGPT', stderr='')
            result = native_tools.codex_authentication({})
            self.assertEqual(result['status'], 'Signed in')
            self.assertIn('not been tested', result['detail'])
            check.return_value = MagicMock(returncode=0, stdout='Logged in using API key', stderr='')
            self.assertEqual(native_tools.codex_authentication({})['status'], 'Signed in')
            check.return_value = MagicMock(returncode=1, stdout='Not logged in', stderr='')
            self.assertEqual(native_tools.codex_authentication({})['status'], 'Setup required')
            # Network/server failure is not a license to destroy login state.
            check.return_value = MagicMock(returncode=1, stdout='', stderr='401: secret-token')
            failed = native_tools.codex_authentication({})
            self.assertEqual(failed['status'], 'Error')
            self.assertNotIn('secret-token', repr(failed))
            check.side_effect = native_tools.subprocess.TimeoutExpired(['/codex', 'login', 'status'], 12)
            self.assertEqual(native_tools.codex_authentication({})['status'], 'Error')
            check.assert_called_with(['/codex', 'login', 'status'], capture_output=True,
                                     text=True, timeout=12, stdin=native_tools.subprocess.DEVNULL)
        with patch('native_tools.discover', side_effect=RuntimeError('not found')):
            self.assertEqual(native_tools.codex_authentication({})['status'], 'Missing')

    def test_codex_login_uses_official_cli_and_terminal_without_shell(self):
        with patch('native_tools.discover', return_value='/codex'), \
             patch('core.terminal_args', return_value=['/usr/bin/xfce4-terminal', '--command=/codex login']) as terminal, \
             patch('native_tools.subprocess.Popen') as launch:
            native_tools.begin_codex_login({})
            terminal.assert_called_once_with(['/codex', 'login'])
            self.assertEqual(launch.call_args.args[0][0], '/usr/bin/xfce4-terminal')
            self.assertNotIn('shell', launch.call_args.kwargs)
            terminal.reset_mock()
            native_tools.begin_codex_login({}, device_auth=True)
            terminal.assert_called_once_with(['/codex', 'login', '--device-auth'])

if __name__ == '__main__':
    unittest.main()
