import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
from gi.repository import Gio, GLib
from file_browser import RemoteFolder
import desktop_helper
import project_client

class FolderRoutes(unittest.TestCase):
    def folder(self):
        with patch('file_browser.Gio.File.new_for_uri'):
            result = RemoteFolder(None, 'sftp://optiplex@100.121.156.34/home/optiplex/StudioProjects/Godot/game', MagicMock(), MagicMock())
        return result

    def test_missing_backend_reports_actionable_error(self):
        folder = self.folder()
        with patch('file_browser.Gio.Vfs.get_default') as vfs:
            vfs.return_value.get_supported_uri_schemes.return_value = ['file']
            folder.start()
        self.assertIn('gvfs-backends', folder.finished.call_args.args[1])
        folder.file.query_info_async.assert_not_called()

    def test_unmounted_folder_mounts_then_checks_before_open(self):
        folder = self.folder()
        folder.file.query_info_finish.side_effect = GLib.Error.new_literal(Gio.io_error_quark(), 'not mounted', Gio.IOErrorEnum.NOT_MOUNTED)
        with patch('file_browser.Gtk.MountOperation.new'):
            folder.checked(folder.file, None)
        folder.file.mount_enclosing_volume.assert_called_once()
        folder.file.query_info_finish.side_effect = None
        folder.mounted(folder.file, None)
        folder.file.query_info_async.assert_called_once()
        folder.finished.assert_not_called()

    def test_connection_error_is_visible_and_never_opens_manager(self):
        folder = self.folder()
        folder.file.query_info_finish.side_effect = GLib.Error.new_literal(Gio.io_error_quark(), 'Permission denied', Gio.IOErrorEnum.PERMISSION_DENIED)
        folder.checked(folder.file, None)
        self.assertIn('Permission denied', folder.finished.call_args.args[1])
        folder.end(error='second error')
        folder.finished.assert_called_once()

    def test_missing_fuse_path_falls_back_to_native_browser(self):
        folder = self.folder()
        folder.file.get_path.return_value = None
        folder.native_browser = MagicMock()
        with patch('file_browser.Gio.AppInfo.get_default_for_type', return_value=None):
            folder.open()
        folder.native_browser.assert_called_once()
        folder.finished.assert_not_called()

    def test_local_mounted_path_is_passed_to_directory_handler(self):
        folder = self.folder()
        with tempfile.TemporaryDirectory() as directory:
            folder.file.get_path.return_value = directory
            manager = MagicMock()
            manager.launch.return_value = True
            manager.get_display_name.return_value = 'File Manager'
            with patch('file_browser.Gio.AppInfo.get_default_for_type', return_value=manager):
                folder.open()
            self.assertEqual(manager.launch.call_args.args[0][0].get_path(), directory)
        self.assertIsNone(folder.finished.call_args.args[1])

    def test_false_launch_result_falls_back_instead_of_claiming_success(self):
        folder = self.folder()
        folder.native_browser = MagicMock()
        with tempfile.TemporaryDirectory() as directory:
            folder.file.get_path.return_value = directory
            manager = MagicMock()
            manager.launch.return_value = False
            with patch('file_browser.Gio.AppInfo.get_default_for_type', return_value=manager):
                folder.open()
        folder.native_browser.assert_called_once()
        folder.finished.assert_not_called()

    def test_both_gui_buttons_use_selected_project_and_error_dialog(self):
        from test_projects import GUIActions
        fake = GUIActions().fake()
        for assets in (False, True):
            routes=[]
            def factory(parent, uri, finished, status):
                routes.append(uri)
                result=MagicMock()
                result.start.side_effect=lambda: finished(None,'SFTP authentication failed')
                return result
            with patch('project_ui.client.request', return_value={}) as request, patch('file_browser.RemoteFolder', side_effect=factory), patch('project_ui.GLib.idle_add'):
                fake.browse_remote_folder(assets)
            self.assertEqual(request.call_args.args[2], 'browse' if assets else 'browse_project')
            self.assertEqual(routes[0], project_client.project_uri(fake.config,'game',assets))
            self.assertEqual(fake.last_notice[0], 'Cannot open project folder')
            self.assertFalse(fake.busy)

class DesktopEnvironment(unittest.TestCase):
    env={'DISPLAY': ':0', 'XDG_RUNTIME_DIR': '/run/user/wolf', 'WAYLAND_DISPLAY':'wayland-1'}

    def test_all_applications_use_discovered_socket_and_one_launch(self):
        for application in ('godot','krita','blender'):
            calls=[]
            polls=[0]
            def run(args, **kwargs):
                calls.append(args)
                if args[1]=='top':
                    polls[0]+=1
                    if polls[0]<12:return 'COMMAND\n'
                    return 'COMMAND\n/app/bin/'+application+(' --editor --path /projects/Godot/game' if application=='godot' else '')+'\n'
                return ''
            with patch('desktop_helper.desktop_environment',return_value=self.env), patch('desktop_helper.run',side_effect=run), patch('desktop_helper.time.sleep'):
                desktop_helper.launch_and_confirm('WolfStudioDesktop_123',application,'game')
            launches=[c for c in calls if '-d' in c]
            self.assertEqual(len(launches),1)
            self.assertIn('WAYLAND_DISPLAY=wayland-1',launches[0])
            self.assertNotIn('WAYLAND_DISPLAY=wayland-2',launches[0])
            self.assertIn(desktop_helper.APPS[application],launches[0])
            self.assertGreater(polls[0],8)

    def test_bad_environment_is_rejected(self):
        with patch('desktop_helper.run',return_value=json.dumps(dict(self.env,WAYLAND_DISPLAY='../secret'))):
            with self.assertRaises(ValueError):desktop_helper.desktop_environment('WolfStudioDesktop_123')

    def test_probe_discovers_existing_socket_not_old_hardcoded_value(self):
        with tempfile.TemporaryDirectory() as directory:
            sock=socket.socket(socket.AF_UNIX)
            try:
                sock.bind(str(Path(directory)/'wayland-1'))
                source=desktop_helper.ENVIRONMENT_SOURCE.replace("Path('/run/user/wolf')",'Path('+repr(directory)+')')
                result=subprocess.check_output(['/usr/bin/python3','-c',source],env=dict(os.environ,WAYLAND_DISPLAY='wayland-2'),text=True)
                self.assertEqual(json.loads(result)['WAYLAND_DISPLAY'],'wayland-1')
            finally:sock.close()
