"""Regression checks for Docker top process detection. No Docker required."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('desktop_helper', ROOT / 'studio' / 'desktop_helper.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class DesktopProcessTests(unittest.TestCase):
    def test_godot_process_with_pid(self):
        ps = 'PID COMMAND\n107 /app/bin/godot --editor --path /projects/Godot/MyGame\n'
        self.assertTrue(helper.matching_process(ps, 'godot', 'MyGame'))
        self.assertFalse(helper.matching_process(ps, 'godot', 'OtherGame'))

    def test_krita_process_with_pid(self):
        ps = 'PID COMMAND\n222 /app/bin/krita /tmp/drawing.kra\n'
        self.assertTrue(helper.matching_process(ps, 'krita', '__desktop__'))

    def test_wrapper_does_not_count(self):
        ps = 'PID COMMAND\n222 /bin/sh -c krita\n'
        self.assertFalse(helper.matching_process(ps, 'krita', '__desktop__'))

    def test_docker_top_always_requests_pid(self):
        import inspect
        source = inspect.getsource(helper)
        self.assertNotIn("['docker', 'top', container, '-eo', 'args']", source)
        self.assertEqual(source.count("['docker', 'top', container, '-eo', 'pid,args']"), 2)


if __name__ == '__main__':
    unittest.main()
