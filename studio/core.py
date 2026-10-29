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


CHARACTER_STUDY_PROMPT = """Create a non-destructive character study in THIS Studio Project using the registered
studio-mpfb and studio-blender MCP servers. This is a visual art-direction task,
not a software-installation task. First query MPFB status and Blender scene.
If either server, system asset pack or live Blender connection is missing,
state which check failed and stop; do not claim that modeling succeeded.
Use an anatomically coherent MPFB base, then vary proportions and expression
with a deliberate asymmetric silhouette. Save an editable .blend in models/
and a separate glTF/.glb export in assets/3d/ with new names; do not modify
or overwrite existing Patient files or other project sources.
Use Blender visual tools to inspect front, side and three-quarter views,
then make one measured refinement from that feedback. If images are not
visible through Studio's client, report that and request a screenshot;
do not fabricate visual judgments. Record exact generated file paths,
observed MCP tool results and remaining artistic issues. Keep Rigger disabled
and do not initiate video or mocap. Confirm with the user before destructive
actions or before changing existing scenes."""

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
