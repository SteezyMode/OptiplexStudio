"""Regression tests for Wolf Godot project discovery and non-destructive sync."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

SPEC = spec_from_file_location("studio_wolf_godot", Path(__file__).resolve().parents[1]
                               / "tools/sync_wolf_godot_projects.py")
mod = module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


class FakeDocker:
    def __init__(self, root, containers=None):
        self.root = root
        self.containers = containers or ["WolfStudioDesktop_123"]
        self.configs = {c: "[/projects/Godot/studio-sandbox]\n\nfavorite=true\n"
                        for c in self.containers}
        self.calls = []

    def __call__(self, args, **kwargs):
        self.calls.append(args)
        if args[:2] == ["docker", "ps"]:
            return subprocess.CompletedProcess(args, 0, "\n".join(self.containers), "")
        if args[:2] == ["docker", "inspect"]:
            source = str(self.root)
            return subprocess.CompletedProcess(args, 0,
                json.dumps([{"Source": source, "Destination": "/projects", "Type": "bind"}]), "")
        if args[:2] == ["docker", "exec"]:
            container = args[5]
            incoming = json.loads(kwargs["input"])
            self.assert_allowed(incoming)
            original = self.configs[container]
            for path in incoming:
                if f"[{path}]" not in original:
                    original += f"\n[{path}]\n\nfavorite=false\n"
            self.configs[container] = original
            return subprocess.CompletedProcess(args, 0, "registered", "")
        raise AssertionError(f"Unexpected docker call: {args}")

    def assert_allowed(self, paths):
        assert all(p.startswith("/projects/Godot/") or
                   p.startswith("/projects/.studio/art-director/comparisons/") for p in paths)


class RegistrarTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "StudioProjects"
        self.root.mkdir()
        self.godot = self.root / "Godot"
        self.godot.mkdir()
        self.create(self.godot / "threshold")
        self.create(self.godot / "studio-sandbox")
        self.trial = self.root / ".studio/art-director/comparisons/patient-v2/animation-trial-01/project"
        self.create(self.trial)

    @staticmethod
    def create(p):
        p.mkdir(parents=True, exist_ok=True)
        (p / "project.godot").write_text("config_version=5\n")

    def test_only_approved_project_roots(self):
        self.assertEqual(mod.project_names(self.root), [
            "/projects/.studio/art-director/comparisons/patient-v2/animation-trial-01/project",
            "/projects/Godot/studio-sandbox", "/projects/Godot/threshold"])

    def test_nested_symlinks_and_nonprojects_not_traversed(self):
        outside = Path(self.tmp.name) / "outside"
        self.create(outside / "wrong")
        (self.godot / "bad-symlink").symlink_to(outside / "wrong", target_is_directory=True)
        (self.godot / "empty").mkdir()
        hidden = self.trial.parent / "assets"
        self.create(hidden / "wrong")
        self.assertEqual(len(mod.project_names(self.root)), 3)

    def test_reconnect_is_idempotent_and_preserves_favorites(self):
        docker = FakeDocker(self.root)
        self.assertEqual(mod.synchronize(self.root, run=docker), 0)
        first = docker.configs["WolfStudioDesktop_123"]
        self.assertIn("[/projects/Godot/threshold]", first)
        self.assertIn("favorite=true", first)
        self.assertEqual(mod.synchronize(self.root, run=docker), 0)
        self.assertEqual(first, docker.configs["WolfStudioDesktop_123"])
        self.assertFalse(any(args[1] in ("run", "restart", "rm", "stop") for args in docker.calls))

    def test_recreated_container_gets_same_project_list(self):
        docker = FakeDocker(self.root)
        self.assertEqual(mod.synchronize(self.root, run=docker), 0)
        docker.containers = ["WolfStudioDesktop_999"]
        docker.configs["WolfStudioDesktop_999"] = ""
        self.assertEqual(mod.synchronize(self.root, run=docker), 0)
        self.assertIn("[/projects/Godot/threshold]", docker.configs["WolfStudioDesktop_999"])

    def test_missing_desktop_exits_without_creating_one(self):
        docker = FakeDocker(self.root)
        docker.containers = []
        self.assertEqual(mod.synchronize(self.root, run=docker), 0)
        self.assertFalse(any(args[1] == "exec" for args in docker.calls))

    def test_wrong_mount_never_mutates_container(self):
        docker = FakeDocker(self.root)
        def wrong(args, **kwargs):
            if args[1] == "inspect":
                return subprocess.CompletedProcess(args, 0,
                    json.dumps([{"Source": "/other", "Destination": "/projects", "Type": "bind"}]), "")
            return docker(args, **kwargs)
        self.assertEqual(mod.synchronize(self.root, run=wrong), 0)
        self.assertFalse(any(args[1] == "exec" for args in docker.calls))

    def test_multiple_wolf_desktops_synced(self):
        docker = FakeDocker(self.root, containers=["WolfStudioDesktop_123", "WolfStudioDesktop_456"])
        self.assertEqual(mod.synchronize(self.root, run=docker), 0)
        self.assertTrue(all("[/projects/Godot/threshold]" in cfg for cfg in docker.configs.values()))

    def test_bad_docker_result_returns_failure(self):
        docker = FakeDocker(self.root)
        def fails(args, **kwargs):
            if args[1] == "exec":
                return subprocess.CompletedProcess(args, 1, "", "Permission denied")
            return docker(args, **kwargs)
        self.assertEqual(mod.synchronize(self.root, run=fails), 1)

    def test_remote_script_syntax(self):
        compile(mod.REMOTE, "<godot-registry-sync>", "exec")


if __name__ == "__main__":
    unittest.main()
