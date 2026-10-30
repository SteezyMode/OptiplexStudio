"""Workbench creation/edit/play and project-affinity regression tests."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import app
import native_tools
import project_helper


class PlayRoundtrip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.config = {'projects_dir': str(self.path)}
        project_helper.create_project(self.path, 'forest', 'Studio')

    def test_play_uses_exact_selected_project_without_editor_flag(self):
        with patch('native_tools.discover', return_value='/usr/bin/godot'), \
             patch('native_tools.subprocess.Popen') as popen:
            result = native_tools.launch_game(self.config, 'forest')
        command = popen.call_args.args[0]
        self.assertEqual(command, ['/usr/bin/godot', '--path', str(self.path / 'forest')])
        self.assertNotIn('--editor', command)
        self.assertEqual(popen.call_args.kwargs['cwd'], str(self.path / 'forest'))
        self.assertIn('Check the game window', result)

    def test_missing_godot_scaffold_and_traversal_fail_before_launch(self):
        (self.path / 'forest/project.godot').unlink()
        with patch('native_tools.discover', return_value='/usr/bin/godot'), \
             patch('native_tools.subprocess.Popen') as popen:
            with self.assertRaisesRegex(ValueError, 'no valid Godot scaffold'):
                native_tools.launch_game(self.config, 'forest')
            with self.assertRaises(ValueError):
                native_tools.launch_game(self.config, '../outside')
            popen.assert_not_called()


class ProjectAffinity(unittest.TestCase):
    def fake(self, turn=None):
        from test_projects import GUIActions
        from ui_fakes import Widget
        fake = GUIActions().fake()
        fake.rows = [{'name': 'first', 'has_godot': True}, {'name': 'second', 'has_godot': True}]
        fake.project_buttons, fake.godot_buttons = [Widget()], [Widget()]
        fake.active_label, fake.detail = Widget(), Widget()
        fake.combo.get_active_id.return_value = 'second'
        fake.last_project = 'second'
        old = MagicMock()
        old.alive = True
        old.project = 'first'
        old.conversation.turn = turn
        fake.embedded_view = old
        return fake, old

    def test_switching_projects_closes_old_finished_conversation(self):
        fake, old = self.fake()
        app.Studio.selection_changed(fake, None)
        old.close.assert_called_once_with()
        self.assertTrue(fake.project_buttons[0].sensitive)

    def test_switching_during_active_ai_turn_is_blocked(self):
        fake, old = self.fake(turn='active-turn')
        app.Studio.selection_changed(fake, None)
        old.close.assert_not_called()
        fake.combo.set_active_id.assert_called_with('first')
        self.assertIn('Finish or interrupt', fake.status.text)


if __name__ == '__main__':
    unittest.main()
