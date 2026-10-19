"""Native Creative Tools screen: only confirmed Studio launch actions.

Every entry must have an actual, tested handler. Candidate editors belong in
the roadmap until their host availability and project integration are verified.
The retired browser editor catalog remains in Git history, not this UI.
"""

TOOL_GROUPS = (
    {
        'title': 'DESKTOP ACCESS',
        'description': 'Connect to the existing remote workspace.',
        'tools': (
            ('Studio Desktop', 'desktop', 'Open the current Wolf desktop session.'),
            ('Moonlight', 'moonlight', 'Open the existing streaming client.'),
        ),
    },
    {
        'title': 'GAME PROJECT',
        'description': 'Edit and preview the selected game.',
        'tools': (
            ('Godot', 'godot', 'Open or focus the selected Godot project.'),
        ),
    },
    {
        'title': 'ART & 3D',
        'description': 'Open installed creative programs in the Wolf desktop.',
        'tools': (
            ('Blender', 'blender', 'Model, texture and animate 3D assets.'),
            ('Krita', 'krita', 'Paint textures and illustrations.'),
        ),
    },
)

READY_ACTIONS = frozenset(('desktop', 'moonlight', 'godot', 'blender', 'krita'))
