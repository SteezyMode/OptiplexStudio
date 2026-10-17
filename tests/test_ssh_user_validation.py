"""Regression tests for shared SSH user validation and command construction."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'studio'))
import core


class SSHUserTests(unittest.TestCase):
    def test_valid_users(self):
        for username in ('optiplex', 'root', '_service', 'user-1'):
            with self.subTest(username=username):
                self.assertEqual(core.valid_ssh_user(username), username)
                command = core.ssh_args({'host': '100.100.100.100', 'user': username}, 'edit', 'demo')
                self.assertIn(f'{username}@100.100.100.100', command)

    def test_invalid_users_are_rejected_in_both_paths(self):
        for username in ('', '1user', 'name with space', 'a;touch /tmp/bad', 'a' * 65, None, 5):
            with self.subTest(username=username):
                with self.assertRaisesRegex(ValueError, 'valid SSH user'):
                    core.valid_ssh_user(username)
                with self.assertRaisesRegex(ValueError, 'valid SSH user'):
                    core.remote_command('edit', 'demo', username)
                with self.assertRaisesRegex(ValueError, 'valid SSH user'):
                    core.ssh_args({'host': '100.100.100.100', 'user': username}, 'edit', 'demo')


if __name__ == '__main__':
    unittest.main()
