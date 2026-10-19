"""Creative Tools catalog: capabilities first, verified native actions only.

This is deliberately data-only. Candidate tools are not installed, invoked, or
advertised as working from the UI until the corresponding adapter has tests.
The previously hosted browser editors are outside Studio's tool catalog.
"""

TOOL_GROUPS = (
    {
        "title": "WORKSPACE",
        "description": "Connect to your existing streamed desktop or open Moonlight.",
        "tools": (
            ("Studio Desktop", "desktop", "Open the existing Wolf workspace.", "ready"),
            ("Moonlight", "moonlight", "Open the streaming client.", "ready"),
        ),
    },
    {
        "title": "GAME & CODE",
        "description": "Edit scenes, run your game and work with source code.",
        "tools": (
            ("Godot", "godot", "Open the selected Godot project.", "ready"),
            ("Zed / VSCodium", None, "Coding editor pilot; no adapter installed by Studio.", "evaluation"),
        ),
    },
    {
        "title": "3D & ANIMATION",
        "description": "Models, materials, rigging and animation.",
        "tools": (
            ("Blender", "blender", "Open in the existing Wolf desktop.", "ready"),
            ("Blockbench", None, "Evaluate a native low-poly workflow alongside Blender.", "evaluation"),
        ),
    },
    {
        "title": "2D & PIXEL ART",
        "description": "Textures, sprites, frame animation and game art.",
        "tools": (
            ("Krita", "krita", "Open in the existing Wolf desktop.", "ready"),
            ("LibreSprite / Aseprite", None, "Native pixel editor comparison; not yet integrated.", "evaluation"),
        ),
    },
    {
        "title": "MUSIC & SOUND",
        "description": "Compose scores and prepare effects for Godot.",
        "tools": (
            ("LMMS / SunVox", None, "Native composition workflow to validate.", "evaluation"),
            ("Audacity", None, "Native sound-effect editor to validate.", "evaluation"),
        ),
    },
)

READY_ACTIONS = frozenset(("desktop", "moonlight", "godot", "blender", "krita"))
