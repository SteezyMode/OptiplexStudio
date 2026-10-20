"""Session-only command aliases. Tool files remain outside sandbox writable roots."""
import os
from pathlib import Path
import shlex
import tempfile
import native_tools


class ToolEnvironment:
    def __init__(self, config, cwd):
        self.directory = tempfile.TemporaryDirectory(prefix='studio-tool-path-', dir='/tmp')
        self.paths = {}
        root = Path(self.directory.name)
        if root.resolve().is_relative_to(cwd.resolve()):
            self.directory.cleanup()
            raise ValueError('Tool aliases must be outside the selected Project.')
        for app, aliases in native_tools.ADAPTERS.items():
            if app == 'codex':
                continue
            try:
                executable = native_tools.discover(config, app)
            except (ValueError, OSError, RuntimeError):
                continue
            self.paths[app] = executable
            for alias in aliases:
                script = '#!/bin/sh\n'
                if app == 'godot':
                    # Headless imports may write engine caches/user data. Keep them
                    # in this Project, never make HOME or managed tools writable.
                    data = str(cwd / '.studio' / 'headless')
                    script += ('for arg do\n if [ "$arg" = "--headless" ]; then\n'
                               ' export XDG_DATA_HOME=' + shlex.quote(data + '/data') + '\n'
                               ' export XDG_CONFIG_HOME=' + shlex.quote(data + '/config') + '\n'
                               ' export XDG_CACHE_HOME=' + shlex.quote(data + '/cache') + '\n'
                               ' break\n fi\ndone\n')
                script += 'exec ' + shlex.quote(executable) + ' "$@"\n'
                target = root / alias
                target.write_text(script)
                target.chmod(0o700)
        # Drop relative/empty PATH entries so the project cannot shadow system tools.
        original = [p for p in os.get_exec_path() if Path(p).is_absolute()]
        companions = []
        try:
            codex = Path(native_tools.discover(config, 'codex'))
            from codex_install import inspect_runtime
            if inspect_runtime(codex)['status'] == 'Components verified':
                companions.append(str(codex.parent.parent / 'codex-path'))
        except (ValueError, OSError, RuntimeError):
            pass
        self.path = os.pathsep.join([str(root), *companions, *original])

    def config(self):
        return {'allow_login_shell': False,
                'shell_environment_policy': {'set': {'PATH': self.path}}}

    def close(self):
        self.directory.cleanup()
