"""Project-aware tool capabilities: safe legacy Godot upgrade and native launch paths."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import native_tools
import project_client


class ProjectCapabilities(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = {'projects_dir': str(self.root)}

    def legacy(self, kind='Blank'):
        project = self.root / 'legacy'
        project.mkdir()
        (project / 'studio-project.json').write_text(json.dumps({'version': 1, 'type': kind}) + '\n')
        (project / 'GAME.md').write_text('Original creative direction — preserve\n')
        (project / 'music').mkdir()
        (project / 'music' / 'track.mmp').write_text('Editable audio source')
        return project

    def check(self, operation='list_projects', project='Studio'):
        return project_client.request(self.config, project, operation)

    def test_legacy_blank_can_add_godot_without_modifying_existing_files(self):
        root = self.legacy()
        preserved = {str(p.relative_to(root)): p.read_bytes()
                     for p in root.rglob('*') if p.is_file()}
        self.assertFalse(self.check()[0]['has_godot'])
        first = self.check('ensure_godot', 'legacy')
        self.assertEqual(first, {'ready': True, 'created': ['scenes/main.tscn', 'project.godot']})
        self.assertTrue((root / 'project.godot').is_file())
        self.assertTrue((root / 'scenes/main.tscn').is_file())
        self.assertTrue(self.check()[0]['has_godot'])
        for name, data in preserved.items():
            self.assertEqual((root / name).read_bytes(), data)
        self.assertEqual(self.check('ensure_godot', 'legacy'),
                         {'ready': True, 'created': []})

    def test_existing_scene_never_overwritten_or_manifest_migrated(self):
        root = self.legacy('Music/Audio')
        (root / 'scenes').mkdir()
        original = b'[gd_scene format=3]\n[node name="Existing" type="Node2D"]\n'
        (root / 'scenes' / 'main.tscn').write_bytes(original)
        manifest = (root / 'studio-project.json').read_bytes()
        result = self.check('ensure_godot', 'legacy')
        self.assertEqual(result['created'], ['project.godot'])
        self.assertEqual((root / 'scenes/main.tscn').read_bytes(), original)
        self.assertEqual((root / 'studio-project.json').read_bytes(), manifest)

    def test_existing_godot_scaffold_is_not_repaired_or_replaced(self):
        root = self.legacy('Godot')
        custom = b'config_version=5\n[application]\nconfig/name="Custom"\n'
        (root / 'project.godot').write_bytes(custom)
        self.assertEqual(self.check('ensure_godot', 'legacy'),
                         {'ready': True, 'created': []})
        self.assertEqual((root / 'project.godot').read_bytes(), custom)
        self.assertFalse((root / 'scenes').exists())

    def test_symlinked_godot_file_is_not_followed_or_overwritten(self):
        root = self.legacy()
        outside = self.root / 'outside.godot'
        outside.write_text('outside')
        (root / 'project.godot').symlink_to(outside)
        with self.assertRaises(OSError):
            self.check('ensure_godot', 'legacy')
        self.assertEqual(outside.read_text(), 'outside')
        self.assertTrue((root / 'project.godot').is_symlink())

    def test_missing_project_is_not_silently_created(self):
        with self.assertRaises(OSError):
            self.check('ensure_godot', 'nonexistent')

    def test_tools_start_in_project_owned_folders_without_file_argv(self):
        root = self.legacy()
        (root / 'models').mkdir()
        (root / 'art').mkdir()
        tool_dirs = {'blender': 'models', 'blockbench': 'models',
                     'lmms': 'music', 'krita': 'art'}
        with patch('native_tools.discover', side_effect=lambda config, tool: '/bin/' + tool):
            for tool, folder in tool_dirs.items():
                with self.subTest(tool=tool):
                    argv, cwd = native_tools.command(self.config, tool, 'legacy')
                    self.assertEqual(argv, ['/bin/' + tool])
                    self.assertEqual(cwd, root / folder)
            argv, cwd = native_tools.command(self.config, 'vscodium', 'legacy')
            self.assertEqual(argv, ['/bin/vscodium', '--', str(root)])
            self.assertEqual(cwd, root)

    def test_missing_or_symlinked_native_folder_falls_back_inside_project(self):
        root = self.legacy()
        outside = self.root / 'outside'
        outside.mkdir()
        (root / 'models').symlink_to(outside, target_is_directory=True)
        with patch('native_tools.discover', return_value='/bin/blender'):
            self.assertEqual(native_tools.command(self.config, 'blender', 'legacy')[1], root)
        with patch('native_tools.discover', return_value='/bin/krita'):
            self.assertEqual(native_tools.command(self.config, 'krita', 'legacy')[1], root)

    def test_godot_requires_actual_scaffold(self):
        root = self.legacy()
        with patch('native_tools.discover', return_value='/bin/godot'):
            with self.assertRaisesRegex(ValueError, 'Add Godot'):
                native_tools.command(self.config, 'godot', 'legacy')
            self.check('ensure_godot', 'legacy')
            argv, cwd = native_tools.command(self.config, 'godot', 'legacy')
            self.assertEqual(argv, ['/bin/godot', '--editor', '--path', str(root)])
            self.assertEqual(cwd, root)


class ProjectCapabilityUI(unittest.TestCase):
    def test_missing_capability_disables_godot_only_actions(self):
        import app
        fake = MagicMock()
        fake.combo.get_active_id.return_value = 'legacy'
        fake.rows = [{'name': 'legacy', 'has_godot': False}]
        fake.project_buttons = [MagicMock()]
        fake.godot_buttons = [MagicMock()]
        fake.tray_project_items = []
        fake.busy = False
        fake.last_project = 'legacy'
        with patch('app.Studio.update_ai_run'):
            app.Studio.selection_changed(fake, None)
            fake.godot_buttons[0].set_sensitive.assert_called_with(False)
            fake.add_godot_button.set_sensitive.assert_called_with(True)
            fake.project_buttons[0].set_sensitive.assert_called_with(True)
            self.assertIn('Add Godot', fake.godot_capability_note.set_text.call_args.args[0])
            fake.rows = [{'name': 'legacy', 'has_godot': True}]
            app.Studio.selection_changed(fake, None)
            fake.godot_buttons[0].set_sensitive.assert_called_with(True)
            fake.add_godot_button.set_sensitive.assert_called_with(False)


if __name__ == '__main__':
    unittest.main()
