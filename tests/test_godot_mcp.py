"""Project-scoped Godot MCP configuration regression tests."""
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "studio"))
import godot_mcp


class GodotMCPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "project.godot").write_text("[application]\n", encoding="utf-8")
        self.tool = self.root / "godot-editor-mcp"
        self.tool.write_text("test executable", encoding="utf-8")

    def test_opt_in_creates_project_local_config_only(self):
        target = godot_mcp.enable(self.root, self.tool)
        self.assertEqual(target, self.root / ".codex" / "config.toml")
        value = target.read_text()
        self.assertIn("[mcp_servers.godot]", value)
        self.assertIn(str(self.tool), value)
        self.assertNotIn("http://", value)
        self.assertNotIn("9090", value)
        with self.assertRaises(FileExistsError):
            godot_mcp.enable(self.root, self.tool)
        self.assertEqual(value, target.read_text())

    def test_bridge_check_reports_listener_without_claiming_mcp(self):
        class FakeSocket:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with patch("socket.create_connection", return_value=FakeSocket()) as connect:
            self.assertTrue(godot_mcp.bridge_status())
            connect.assert_called_once_with(("127.0.0.1", 9080), timeout=1)

    def test_bridge_check_handles_unreachable_listener(self):
        with patch("socket.create_connection", side_effect=ConnectionRefusedError):
            self.assertFalse(godot_mcp.bridge_status())
        with self.assertRaises(ValueError):
            godot_mcp.bridge_status("0.0.0.0", 9080)

    def test_missing_godot_project_fails(self):
        (self.root / "project.godot").unlink()
        with self.assertRaises(ValueError):
            godot_mcp.project_configuration(self.root, self.tool)

    def test_existing_config_is_preserved(self):
        folder = self.root / ".codex"
        folder.mkdir()
        (folder / "config.toml").write_text("[other]\n")
        with self.assertRaises(FileExistsError):
            godot_mcp.enable(self.root, self.tool)
        self.assertEqual((folder / "config.toml").read_text(), "[other]\n")

    def test_symlink_config_directory_is_rejected(self):
        other = self.root / "elsewhere"
        other.mkdir()
        (self.root / ".codex").symlink_to(other, target_is_directory=True)
        with self.assertRaises(ValueError):
            godot_mcp.enable(self.root, self.tool)
        self.assertEqual(list(other.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
