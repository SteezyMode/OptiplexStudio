"""Local project utilities and native terminal command selection."""
import shlex
import shutil
from pathlib import Path


def valid_name(name):
    import re
    return isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,128}', name) is not None


def terminal_args(command):
    # Use each terminal's command parsing contract. XFCE may hand off to a server.
    # In particular, cosmic-term's help does not promise -e support.
    adapters = {
        'gnome-terminal': ['--wait', '--'],
        'konsole': ['--nofork', '-e'],
        'xfce4-terminal': ['--window'],
        'xterm': ['-e'],
    }
    candidates = []
    alternative = shutil.which('x-terminal-emulator')
    if alternative:
        resolved = Path(alternative).resolve().name
        if resolved in adapters:
            candidates.append((alternative, resolved))
    candidates.extend((name, name) for name in adapters if shutil.which(name))
    if candidates:
        executable, adapter = candidates[0]
        if adapter == 'xfce4-terminal':
            # XFCE parses this with GLib shell argv parsing, without a shell.
            return [executable, '--window', '--command=' + shlex.join(command)]
        return [executable] + adapters[adapter] + command
    raise RuntimeError('Install a supported terminal: xterm, GNOME Terminal, Konsole or XFCE Terminal.')


CODEX_TASKS = {
    'Review Changes': 'Read AGENTS.md and the project documents. Review current uncommitted changes for defects and risks. Report findings without changing files or committing.',
    'Explain Project': 'Read AGENTS.md and the project documents. Explain this project, its structure, current state, and useful next steps. Do not change files or commit.',
    'Fix Godot Errors': 'Read AGENTS.md and the project documents. Inspect this Godot project, run existing permitted Godot validation when available, and fix confirmed errors. Report unavailable tools or permissions; never bypass permissions or change unrelated system services. Update concise progress and decisions. Do not commit.',
    'Validate Project': 'Read AGENTS.md and the project documents. Run existing permitted Godot project validation when available and report results. Report missing permissions or tools without bypassing them. Do not change files or commit.'}


def projects(config):
    """Discover projects in the configured local workspace."""
    import project_client
    return project_client.request(config, 'Studio', 'list_projects')


def run_action(config, action, name, **callbacks):
    """Run a local project action or create a local project."""
    import native_tools
    if action == 'new':
        import project_client
        return project_client.request(config, name, 'create')
    return native_tools.run_action(config, action, name, **callbacks)
