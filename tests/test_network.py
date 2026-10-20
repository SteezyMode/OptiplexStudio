"""Network and GUI state regression tests; no live service mutations."""
import io
import json
import socket
import ssl
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import core

CONFIG = {'host': '100.100.100.101', 'user': 'optiplex'}

class Networking(unittest.TestCase):
    def test_api_without_dns_preserves_tls_and_host(self):
        raw, tls = MagicMock(), MagicMock()
        payload = b'{"projects":[{"name":"game","dirty":false}]}'
        tls.makefile.return_value = io.BytesIO(b'HTTP/1.1 200 OK\r\nContent-Length: ' + str(len(payload)).encode() + b'\r\n\r\n' + payload)
        with patch('socket.getaddrinfo', side_effect=AssertionError('DNS forbidden')), \
             patch('socket.socket', return_value=raw) as create, \
             patch('ssl.SSLContext.wrap_socket', autospec=True, return_value=tls) as wrap, \
             patch.dict('os.environ', {'HTTPS_PROXY': 'http://unreachable.invalid:8080'}):
            self.assertEqual(core.remote_projects(CONFIG)[0]['name'], 'game')
        create.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        raw.connect.assert_called_once_with((CONFIG['host'], 443))
        context = wrap.call_args.args[0]
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertEqual(wrap.call_args.kwargs['server_hostname'], 'studio.monumentrisk.com')
        sent = b''.join(call.args[0] for call in tls.sendall.call_args_list)
        self.assertIn(b'Host: studio.monumentrisk.com\r\n', sent)
        self.assertIn(b'GET /api/projects HTTP/1.1\r\n', sent)
        tls.close.assert_called_once()

    def test_connection_and_certificate_failures_do_not_fallback(self):
        for error in (TimeoutError('timed out'), ConnectionRefusedError('refused'), ssl.SSLCertVerificationError('certificate mismatch')):
            raw = MagicMock()
            with self.subTest(error=error), patch('socket.socket', return_value=raw), \
                 patch('socket.getaddrinfo', side_effect=AssertionError('DNS fallback forbidden')), \
                 patch('ssl.SSLContext.wrap_socket', side_effect=error):
                with self.assertRaises(type(error)):
                    core.remote_projects(CONFIG)
                raw.close.assert_called_once()

    def test_tcp_connection_failure(self):
        raw = MagicMock()
        raw.connect.side_effect = OSError('network unreachable')
        with patch('socket.socket', return_value=raw), patch('ssl.SSLContext.wrap_socket') as wrap:
            with self.assertRaisesRegex(OSError, 'network unreachable'):
                core.remote_projects(CONFIG)
            wrap.assert_not_called()
            raw.close.assert_called_once()

    def test_api_contract_and_redirect_rejection(self):
        cases = [(302, b'', RuntimeError), (503, b'', RuntimeError),
                 (200, b'not json', ValueError), (200, b'{"projects":[{"name":"../escape"}]}', ValueError),
                 (200, b'x' * (2 * 1024 * 1024 + 1), ValueError)]
        for status, payload, error in cases:
            connection = MagicMock()
            response = connection.getresponse.return_value
            response.status = status
            response.read.return_value = payload
            with self.subTest(status=status, error=error), patch('core.TailscaleHTTPSConnection', return_value=connection):
                with self.assertRaises(error):
                    core.remote_projects(CONFIG)
                connection.close.assert_called_once()

    def test_only_configured_tailnet_ip_allowed_for_api_and_ssh(self):
        for value in ('', 'optiplex', 'studio.monumentrisk.com', '8.8.8.8', '127.0.0.1', '100.128.0.1', '100.63.255.255', '100.100.100.101;id'):
            with self.subTest(value=value), patch('socket.socket') as connect:
                for function in (lambda c: core.remote_projects(c), lambda c: core.ssh_args(c, 'edit', 'game')):
                    with self.assertRaises(ValueError):
                        function(dict(CONFIG, host=value))
                connect.assert_not_called()
        for action in ('new', 'edit', 'code', 'resume'):
            args = core.ssh_args(CONFIG, action, 'game')
            self.assertEqual(args[-2], 'optiplex@' + CONFIG['host'])
            self.assertIn('StrictHostKeyChecking=yes', args)
            self.assertIn('BatchMode=yes', args)

    def test_creative_links_keep_tls_names_and_map_tailnet(self):
        with patch('shutil.which', return_value='/usr/bin/chromium'):
            for _, url in core.APPS + [('Workspace', 'https://studio.monumentrisk.com')]:
                args = core.browser_args(CONFIG, url)
                self.assertEqual(args[-1], url)
                self.assertIn('--host-resolver-rules=MAP monumentrisk.com 100.100.100.101, MAP *.monumentrisk.com 100.100.100.101', args)
                self.assertIn('--proxy-server=direct://', args)
                self.assertFalse(any('ignore-certificate' in arg or 'no-sandbox' in arg for arg in args))
            original = core.browser_args(CONFIG, core.APPS[0][1])
            changed = core.browser_args(dict(CONFIG, host='100.100.100.102'), core.APPS[0][1])
            self.assertNotEqual(original[1], changed[1])
            with self.assertRaises(ValueError):
                core.browser_args(CONFIG, 'https://evil.invalid')
        with patch('shutil.which', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'Install Chromium'):
                core.browser_args(CONFIG, core.APPS[0][1])

    def test_browser_startup_failure(self):
        with patch('core.browser_args', return_value=['/bin/sh', '-c', 'echo browser-failed >&2; exit 7']):
            with self.assertRaisesRegex(RuntimeError, 'browser-failed'):
                core.open_application(CONFIG, core.APPS[0][1])


class Widget:
    def __init__(self):
        self.sensitive = True
        self.text = ''
    def set_sensitive(self, sensitive): self.sensitive = sensitive
    def set_text(self, text): self.text = text

class Combo:
    def __init__(self): self.selected = 'old-game'
    def get_active_id(self): return self.selected
    def remove_all(self): self.selected = None

class GUIState(unittest.TestCase):
    def test_api_failure_clears_selection_and_disables_main_and_tray_actions(self):
        import app
        class Fake:
            config = dict(CONFIG)
            rows = [{'name': 'old-game'}]
            busy = False
            combo = Combo()
            project_buttons = [Widget() for _ in range(3)]
            tray_project_items = [Widget() for _ in range(2)]
            status, detail, refresh_button, create_button = Widget(), Widget(), Widget(), Widget()
            selection_changed = app.Studio.selection_changed
            def worker(self, task, done):
                self.test.assertIsNone(self.combo.get_active_id())
                self.test.assertTrue(all(not b.sensitive for b in self.project_buttons + self.tray_project_items))
                try: result = task()
                except Exception as exc: done(None, str(exc))
                else: done(result, None)
        fake = Fake()
        fake.test = self
        with patch('app.project_client.request', side_effect=OSError('Workspace unreadable')) as projects:
            app.Studio.refresh(fake)
            projects.assert_called_once_with(CONFIG, 'Studio', 'list_projects')
        self.assertEqual(fake.rows, [])
        self.assertIsNone(fake.combo.get_active_id())
        self.assertTrue(all(not b.sensitive for b in fake.project_buttons + fake.tray_project_items))
        self.assertIn('Workspace unavailable: Workspace unreadable', fake.status.text)
        for action in ('edit', 'code', 'resume'):
            with patch('app.core.run_action') as run:
                app.Studio.action(fake, action)
                run.assert_not_called()
                self.assertIn('Select a project', fake.status.text)
