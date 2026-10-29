"""Legacy Studio discovery must preserve existing workspaces without migration."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import project_helper


class LegacyProjects(unittest.TestCase):
    def test_historical_projects_are_discoverable_without_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            expected = []
            before = {}
            for index, kind in enumerate(('Blank', 'Godot', 'Music/Audio', 'Animation', '3D')):
                name = 'legacy_' + str(index)
                folder = workspace / name
                folder.mkdir()
                (folder / 'studio-project.json').write_text(
                    json.dumps({'version': 1, 'type': kind}) + '\n')
                (folder / 'GAME.md').write_text('Original project data')
                expected.append(name)
                before[name] = {p.name: p.read_bytes() for p in folder.iterdir()}
            godot = workspace / 'godot_without_manifest'
            godot.mkdir()
            (godot / 'project.godot').write_text('config_version=5\n')
            before[godot.name] = {'project.godot': (godot / 'project.godot').read_bytes()}
            expected.append(godot.name)
            ordinary = workspace / 'ordinary_directory'
            ordinary.mkdir()
            (ordinary / 'notes.txt').write_text('not a Studio project')

            result = project_helper.handle({'version': 1, 'project': 'Studio',
                'operation': 'list_projects'}, workspace)
            self.assertEqual(sorted(row['name'] for row in result), sorted(expected))
            for name, files in before.items():
                folder = workspace / name
                self.assertEqual({p.name: p.read_bytes() for p in folder.iterdir()}, files)

    def test_invalid_manifests_cannot_bypass_discovery_even_with_godot(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            for index, data in enumerate((
                json.dumps({'version': 999, 'type': 'Studio'}),
                json.dumps({'version': 1, 'type': 'Unknown'}),
                json.dumps(['invalid', 'manifest']),
                '{broken json',
            )):
                folder = workspace / ('bad_' + str(index))
                folder.mkdir()
                (folder / 'studio-project.json').write_text(data)
                (folder / 'project.godot').write_text('config_version=5\n')
            result = project_helper.handle({'version': 1, 'project': 'Studio',
                'operation': 'list_projects'}, workspace)
            self.assertEqual(result, [])

    def test_new_projects_still_use_unified_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            project_helper.create_project(workspace, 'new')
            metadata = json.loads((workspace / 'new/studio-project.json').read_text())
            self.assertEqual(metadata, {'version': 2, 'type': 'Studio', 'engine': 'godot'})
            project = project_helper.Project(workspace, 'new')
            try:
                self.assertEqual(project.kind, 'Studio')
            finally:
                project.close()


if __name__ == '__main__':
    unittest.main()
