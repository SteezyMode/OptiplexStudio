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


CREATIVE_WORKFLOW_GUIDANCE = """Studio is one project-scoped, AI-assisted game creation workspace.
When the user asks to create or change game content, choose tools by the TASK,
not by a named lab. Reuse the selected project's existing files and conventions.
For general 3D assets (props, vegetation, architecture, weapons, environments,
materials, characters) prefer available Blender automation and visual inspection;
use MPFB MCP only when human anatomy or a human rig is relevant. Rigger is
installed but inactive; do not activate it unless the user expressly asks to
test motion capture or retargeting. For scenes, interactions, gameplay and
playable validation use Godot. For music and audio use LMMS when suitable.

Before attempting an integration, check whether the necessary local tool or MCP
server is actually reachable. Missing or incompatible tools are a diagnosis,
NOT a reason to invent results or broaden sandbox permissions. Work only in the
current project; create or update editable source files and export game-ready
assets when requested. Do not overwrite existing work without review; follow
Codex's on-request approval and project-only workspace-write rules. Prefer a
small working result over speculative plugins, infrastructure or setup. When
visual feedback is available, inspect more than one angle before refining.
If image feedback cannot be observed in this client, say so rather than claim
to have seen a render. When possible, test real Godot imports or gameplay,
reporting which checks actually ran. Report created source/export paths,
what was verified, and concrete remaining errors. Do not silently install
tools or start network listeners in response to ordinary creative prompts.
This guidance never authorizes a tool call before the user requests work."""


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
