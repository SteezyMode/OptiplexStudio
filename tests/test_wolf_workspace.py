"""Safe, host-only regression tests for the Wolf AI Workspace command builder."""
import ast
import importlib.util
from pathlib import Path
import os
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'studio/wolf_ai_workspace.py'


class WolfWorkspaceTests(unittest.TestCase):
    def test_syntax(self):
        ast.parse(SOURCE.read_text())

    def test_no_host_token_or_container_privileges(self):
        text = SOURCE.read_text()
        self.assertNotIn('docker.sock', text)
        self.assertNotIn('StrictHostKeyChecking=no', text)
        self.assertIn('IdentitiesOnly=yes', text)
        self.assertIn('ClearAllForwardings=yes', text)

    def test_forced_gate_operations(self):
        text = (ROOT / 'studio/codex_gate.py').read_text()
        self.assertIn("('list', 'new', 'resume')", text)
        self.assertIn('SSH_ORIGINAL_COMMAND', text)
        self.assertIn('uuid.UUID', text)


if __name__ == '__main__':
    unittest.main()
