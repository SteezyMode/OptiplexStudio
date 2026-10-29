"""Codex live-check entry is opt-in, project-bound, and never auto-certifies readiness."""
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
try:
    import gi
    gi.require_version('Gtk', '3.0')
    from tools_ui import ToolsUI, CODEX_LIVE_CHECK
except (ImportError, ValueError):
    ToolsUI = None


@unittest.skipIf(ToolsUI is None, 'GTK introspection unavailable')
class LiveCheck(unittest.TestCase):
    def host(self):
        host = MagicMock()
        host.rows = [{'name': 'alpha'}, {'name': 'beta'}]
        host.combo.get_active_id.return_value = 'alpha'
        host.busy = False
        return host

    def test_check_uses_existing_embedded_project_flow(self):
        host = self.host()
        self.assertFalse(ToolsUI.launch_codex_check(host, 'alpha'))
        host.notebook.set_current_page.assert_called_once_with(1)
        host.open_embedded.assert_called_once_with(prompt=CODEX_LIVE_CHECK)
        self.assertIn('Do not run commands', CODEX_LIVE_CHECK)
        self.assertNotIn('write a file', CODEX_LIVE_CHECK)

    def test_changed_project_does_not_start_model_request(self):
        host = self.host()
        self.assertFalse(ToolsUI.launch_codex_check(host, 'beta'))
        host.open_embedded.assert_not_called()
        host.status.set_text.assert_called_once()
        self.assertIn('not started', host.status.set_text.call_args.args[0])

    def test_project_operation_blocks_live_check(self):
        host = self.host()
        host.busy = True
        self.assertFalse(ToolsUI.launch_codex_check(host, 'alpha'))
        host.open_embedded.assert_not_called()

    def test_removed_project_blocks_live_check(self):
        host = self.host()
        host.rows = []
        self.assertFalse(ToolsUI.launch_codex_check(host, 'alpha'))
        host.open_embedded.assert_not_called()


if __name__ == '__main__':
    unittest.main()
