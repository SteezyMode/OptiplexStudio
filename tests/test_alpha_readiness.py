"""Alpha tool status: honest discovery, actionable missing states, no stale UI."""
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import native_tools


class ReadinessContract(unittest.TestCase):
    def test_executable_discovery_is_not_runtime_ready(self):
        for name in native_tools.CORE_ALPHA_TOOLS[:3]:
            label, attention = native_tools.readiness_summary(
                name, {'status': 'Ready', 'path': '/usr/bin/' + name})
            self.assertIn('launch not verified', label)
            self.assertNotIn('Ready', label)
            self.assertFalse(attention)

    def test_missing_core_four_is_actionable_but_optional_is_neutral(self):
        for name in native_tools.CORE_ALPHA_TOOLS:
            label, attention = native_tools.readiness_summary(name, {'status': 'Missing', 'path': ''})
            self.assertIn('Settings', label)
            self.assertTrue(attention)
        self.assertFalse(native_tools.readiness_summary('krita', {'status': 'Missing'})[1])

    def test_codex_auth_is_distinct_from_live_ai(self):
        observed = {'status': 'Components verified', 'path': '/managed/codex'}
        label, attention = native_tools.readiness_summary('codex', observed, 'Signed in')
        self.assertIn('live AI not verified', label)
        self.assertFalse(attention)
        self.assertTrue(native_tools.readiness_summary('codex', observed, 'Setup required')[1])
        self.assertTrue(native_tools.readiness_summary('codex', observed, 'Error')[1])
        label, attention = native_tools.readiness_summary('codex', {'status': 'Executable detected'})
        self.assertIn('runtime not verified', label)
        self.assertTrue(attention)

    def test_repair_and_failed_configuration_explain_next_step(self):
        for status in ('Repair needed', 'Needs attention', 'Error', 'Broken'):
            label, attention = native_tools.readiness_summary('blender', {'status': status})
            self.assertTrue(attention)
            self.assertIn('Settings', label)

    def test_status_view_never_executes_or_mutates(self):
        result = {'status': 'Ready', 'path': '/untrusted/app', 'detail': 'not checked'}
        before = dict(result)
        with patch('native_tools.subprocess.run', side_effect=AssertionError('no launch')), \
             patch('native_tools.subprocess.Popen', side_effect=AssertionError('no launch')):
            self.assertIn('not verified', native_tools.readiness_summary('godot', result)[0])
        self.assertEqual(result, before)


class HealthRendering(unittest.TestCase):
    def test_core_four_statuses_are_displayed_without_false_green(self):
        import app

        class Host:
            def __init__(self):
                self.config = {'projects_dir': '/fixture'}
                self.window = object()
                self.settings_button = MagicMock()
                self.tool_health_labels = {tool: MagicMock() for tool in native_tools.CORE_ALPHA_TOOLS}

            def worker(self, evaluate, done):
                done(evaluate(), None)

        host = Host()
        def inspect(config, tool):
            if tool == 'godot':
                return {'status': 'Ready', 'path': '/usr/bin/godot'}
            if tool == 'codex':
                return {'status': 'Components verified', 'path': '/managed/codex'}
            return {'status': 'Missing', 'path': ''}
        with patch('native_tools.inspect', side_effect=inspect), \
             patch('native_tools.codex_authentication', return_value={'status': 'Signed in'}):
            app.Studio.refresh_tool_health(host)
        host.tool_health_labels['godot'].set_text.assert_called_with(
            'Godot: Executable detected · launch not verified')
        host.tool_health_labels['codex'].set_text.assert_called_with(
            'Codex: CLI signed in · live AI not verified')
        host.settings_button.set_label.assert_called_with('SETTINGS · ACTION NEEDED')

    def test_late_worker_may_not_replace_newer_result(self):
        import app

        class Host:
            def __init__(self):
                self.config = {'projects_dir': '/fixture'}
                self.window = object()
                self.settings_button = MagicMock()
                self.tool_health_labels = {'godot': MagicMock()}
                self.pending = []
            def worker(self, evaluate, done):
                self.pending.append((evaluate, done))
        host = Host()
        app.Studio.refresh_tool_health(host)
        app.Studio.refresh_tool_health(host)
        with patch('native_tools.inspect', return_value={'status': 'Missing', 'path': ''}):
            host.pending[0][1](({'godot': 'old'}, ['old']), None)
        host.tool_health_labels['godot'].set_text.assert_not_called()
        host.pending[1][1](({'godot': 'new'}, []), None)
        host.tool_health_labels['godot'].set_text.assert_called_once_with('Godot: new')
        host.settings_button.set_label.assert_called_with('SETTINGS')


if __name__ == '__main__':
    unittest.main()
