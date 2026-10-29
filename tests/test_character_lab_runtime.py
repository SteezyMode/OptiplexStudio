"""Direct Character Lab installer tests; never contact network or execute editors."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, call

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import character_lab_runtime as lab


class DirectCharacterLab(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.root = lab.base_directory(self.home)
        self.root.mkdir(parents=True)
        self.blender = self.home / 'blender'
        self.codex = self.home / 'codex'
        for program in (self.blender, self.codex):
            program.write_text('#!/bin/sh\nexit 0\n')
            program.chmod(0o700)

    def test_preflight_refuses_old_blender(self):
        with patch('character_lab_runtime.command',
                   return_value=subprocess.CompletedProcess([], 0, 'Blender 4.5.2\n')):
            with self.assertRaisesRegex(RuntimeError, '5.0'):
                lab.blender_version('/blender')
        with patch('character_lab_runtime.command',
                   return_value=subprocess.CompletedProcess([], 0, 'Blender 5.2.1\n')):
            self.assertEqual(lab.blender_version('/blender'), (5, 2))

    def test_never_overwrites_existing_mcp_servers(self):
        output = subprocess.CompletedProcess([], 0,
            'Name         Command\nstudio-blender  /custom/old-tool\nother  safe\n')
        with patch('character_lab_runtime.command', return_value=output) as run:
            result = lab.register_mcp('/codex', '/mpfb', '/visual')
        self.assertIn('preserved', result['studio-blender'])
        self.assertIn('Registered', result['studio-mpfb'])
        self.assertEqual(run.call_count, 2)
        argv = run.call_args.args[0]
        self.assertEqual(argv[:4], ['/codex', 'mcp', 'add', 'studio-mpfb'])
        self.assertIn('MPFB_BRIDGE_HOST=127.0.0.1', argv)

    def test_both_mcp_entries_are_local_and_visual_is_filtered(self):
        empty = subprocess.CompletedProcess([], 0, 'Name Command\n')
        with patch('character_lab_runtime.command', return_value=empty) as run:
            lab.register_mcp('/codex', '/mpfb', '/visual')
        argv1 = run.call_args_list[1].args[0]
        argv2 = run.call_args_list[2].args[0]
        self.assertEqual(argv1[-1], '/visual')
        self.assertIn('BLENDER_HOST=127.0.0.1', argv1)
        self.assertIn('BLENDER_MCP_SAFE_MODE=1', argv1)
        self.assertIn('DISABLE_TELEMETRY=true', argv1)
        self.assertEqual(argv2[-1], '/mpfb')
        self.assertIn('MPFB_BRIDGE_PORT=9877', argv2)
        self.assertNotIn('0.0.0.0', str(argv1 + argv2))

    def test_real_install_sequence_uses_blender_cli_and_dormant_rigger(self):
        root = self.root
        mpfb_dist = root / 'mpfb-mcp/dist'
        mpfb_dist.mkdir(parents=True)
        (mpfb_dist / 'mpfb_bridge-0.3.0.zip').write_bytes(b'fixture')
        (root / 'visual-mcp/bin').mkdir(parents=True)
        (root / 'visual-mcp/bin/mcp-for-blender').write_bytes(b'fixture')
        rigger = root / 'rigger/dist/rigger-1.2.0.zip'
        rigger.parent.mkdir(parents=True)
        rigger.write_bytes(b'fixture')
        payload = {'mpfb_bridge': str(root / 'mpfb-mcp/bridge/mpfb_bridge'),
                   'rigger_zip': str(rigger), 'mpfb_server': str(root / 'mpfb-mcp/.venv/bin/mpfb-mcp')}
        returned = subprocess.CompletedProcess([], 0, 'Blender 5.2.0\n')
        with patch('character_lab_runtime.prepare', return_value=payload), \
             patch('character_lab_runtime.command', return_value=returned) as cmd, \
             patch('character_lab_runtime.run') as run, \
             patch('character_lab_runtime.register_mcp', return_value={'studio-blender': 'ok'}) as register:
            result = lab.install(str(self.blender), str(self.codex), self.home)
        self.assertEqual(result['blender_version'], (5, 2))
        self.assertEqual(cmd.call_count, 5)
        mpfb = cmd.call_args_list[1].args[0]
        bridge = cmd.call_args_list[2].args[0]
        rig = cmd.call_args_list[3].args[0]
        visual = cmd.call_args_list[4].args[0]
        self.assertIn('install', mpfb)
        self.assertIn('--enable', mpfb)
        self.assertIn('mpfb', mpfb)
        self.assertIn('--enable', bridge)
        self.assertIn('mpfb_bridge-0.3.0.zip', str(bridge))
        self.assertIn('install-file', rig)
        self.assertNotIn('--enable', rig)
        self.assertEqual(visual[-1], 'install-addon')
        self.assertIn('build', run.call_args.args[0])
        register.assert_called_once()

    def test_no_install_if_configured_executables_missing(self):
        with patch('character_lab_runtime.prepare', side_effect=AssertionError('Never prepare')):
            with self.assertRaisesRegex(ValueError, 'missing'):
                lab.install('/missing/blender', str(self.codex), self.home)

    def test_doctor_does_not_claim_tool_protocol_ready(self):
        with patch('character_lab_runtime.socket.create_connection', side_effect=OSError('offline')):
            status = lab.service_status()
        self.assertTrue(all('Offline' in x for x in status.values()))


if __name__ == '__main__':
    unittest.main()
