# Native Tools & Setup beta

The existing wizard offers Install for Godot, Codex, Blender, Krita, Blockbench,
LMMS and VSCodium. Tools remain optional. Choose Executable preserves manual
setup; Auto clears only the selected executable override. Continue permits
incomplete setup. Installation does not edit projects, shell profiles, credentials,
application preferences, system packages or desktop/server services.

## Publisher packages and integrity

| Tool | Automatic Linux package | Integrity source |
| --- | --- | --- |
| Godot | Stable Godot 4 standard ZIP, x86_64/ARM64 | Official release SHA512-SUMS.txt |
| Codex | Canonical runtime package, x86_64/ARM64 (also macOS) | Official GitHub API asset SHA-256 |
| Blender | Official stable Linux tar.xz, matching CPU when published | Blender release SHA-256 manifest |
| Krita | Stable x86_64 type-2 AppImage | KDE download Details SHA-256 |
| Blockbench | Stable x86_64 type-2 AppImage | Official GitHub API asset SHA-256 |
| LMMS | Stable x86_64 type-2 AppImage | Official GitHub API asset SHA-256, if available |
| VSCodium | Stable Linux x64/ARM64 tar.gz | Official GitHub API asset SHA-256 |

Sources: [Godot](https://github.com/godotengine/godot-builds/releases),
[Codex](https://github.com/openai/codex/releases),
[Blender](https://www.blender.org/download/),
[Krita](https://krita.org/en/download/),
[Blockbench](https://github.com/JannisX11/blockbench/releases),
[LMMS](https://github.com/LMMS/lmms/releases), and
[VSCodium](https://github.com/VSCodium/vscodium/releases).

Stable metadata is resolved at setup time. Optional release archives require
matching, unambiguous publisher URLs and checksums. Unsupported CPUs, changed
layouts, absent hashes and network errors stop automation. No unverified package,
mirror-provided hash, package manager or remote script is substituted. In particular,
LMMS 1.2.2 predates GitHub asset digests and may require guided manual setup.
Blender ARM64 requires a matching publisher Linux archive and manifest entry.

HTTPS uses Python certificate verification and a bounded release-host allowlist.
KDE download redirects to unreviewed mirrors fail closed. Use Official guidance
when KDE hosting cannot satisfy this boundary. Publisher hashes protect download
integrity, not compromise of publisher accounts or hosting; independent signature
and attestation verification is not implemented.

## Install, cancel and repair

1. Review discovery. Configured executable paths take priority, followed by PATH,
   ~/.local/bin, and bounded tool roots. Discovery never launches candidates.
2. Install resolves metadata in a background worker. Confirmation shows version,
   exact source URL, checksum source and destination. Each download needs consent.
3. Download progress, verification and extraction appear in the existing wizard.
   Cancel installation or close the wizard to cancel. Cancellation is checked
   between reads and extraction chunks; blocked network reads can take up to the
   30-second socket timeout. Retry or reopen setup after an error.
4. Completed versions are published atomically under
   `~/.local/share/optiplex-studio/tools/TOOL/VERSION/`. Receipts record sources and
   hashes. No sudo, global PATH change, project writes or automatic launch occurs.

Optional tar packages include supporting libraries/resources. Extraction rejects
absolute/traversing/duplicate paths, special files, escaping links, excessive entry
counts and excessive unpacked sizes. Regular files are copied with private modes,
without ownership or setuid bits. Internal regular-file links are copied as files.
Unsupported link layouts fail closed. Downloads are bounded to 1 GiB and optional
unpacked packages to 4 GiB. Godot/Codex keep their existing stricter limits.

AppImages are stored as verified, private executable files. Setup does not invoke
`--appimage-extract`, execute embedded runtimes, mount images, install FUSE, add
`--no-sandbox`, or set sandbox-disabling environment flags. FUSE, graphics/audio
libraries and Electron/user-namespace support must already work on the desktop.
If launch fails, use publisher guidance to install required dependencies or choose
a separately prepared executable. Existing extracted `squashfs-root/AppRun`
installations remain discoverable in manual tool roots. Automatic FUSE-free
AppImage extraction is deliberately unavailable.

Optional managed receipts cover installed files. Recheck identifies missing or
changed payload files; hashes are cached only while filesystem identity, size,
mtime and ctime match. Initial inventory may read large payloads to verify integrity. Repair downloads a fresh verified release into a new sibling
directory and preserves the original directory and saved override. A broken managed
override can resolve its completed repair; valid manual overrides always win.
This is additive repair, not automatic updating or dependency repair. Working
installations disable Install. Codex retains its canonical component repair flow.
Invalid unmanaged overrides require Choose Executable or Auto.

Per-tool process locks prevent concurrent publication. Staging is private and
removed after handled failure/cancellation. Managed destination ancestors cannot
be symlinks. A completed install remains if cancellation arrives after publication.
Abrupt process termination can leave a hidden `.install-*` directory, which is
never discovered; remove it manually while Studio is closed if necessary.

## Embedded shells and headless Godot

Each embedded conversation builds a private temporary directory of shell aliases
from the same discovery results used by native launches. Common commands such as
`godot`, `godot4`, `blender` and `codium` resolve configured or managed executables,
even when their original names include versions or spaces. Arguments are forwarded
literally. Alias files live outside the Project in `/tmp` and receive no sandbox write grant;
project-supplied TMPDIR is ignored. An overlapping Project fails closed.
Reconnect to refresh discovery after setup changes.

Thread start and resume set a session-only PATH and disable login shell semantics,
using the [official Codex configuration options](https://developers.openai.com/codex/config-reference/).
This keeps login profiles from replacing the tool PATH. Verified canonical Codex
`codex-path` companions (including ripgrep) are also retained. User profiles and Codex
configuration files are never edited. Other shell profile customizations are
therefore unavailable in embedded commands; use explicit environment variables
or the existing terminal recovery workflow where needed.

When a Godot alias receives `--headless`, it sets XDG data/config/cache directories
under the verified Project's `.studio/headless/`. Godot imports remain under
`.godot/`. This supports `godot --headless --path "$PWD" --editor --import --quit`
without making HOME writable. The same project-only workspace-write policy,
network restrictions, temporary-directory exclusions, ownership validation,
approval handling and fail-closed live isolation probe remain in force. No tool
root or neighbouring project is added to writable roots. Direct invocation of the
original Godot executable bypasses alias environment handling.

## Validation and remaining limits (2026-10-19)

Run `python3 -B -m unittest discover -s tests -v`. Fixtures cover every optional
publisher, x64 and supported ARM64 archive selection, consent, preservation,
repair, missing digests, changed plans, checksum mismatch, cancellation/cleanup,
unsafe archives, internal link copying, shell argument quoting, headless paths,
managed Godot discovery and the existing project isolation/RPC policy tests.
Wizard fixtures cover all seven install buttons, confirmation, retry and repair.

On this development environment, 243 tests ran successfully with four skips (Unix sockets
prohibited and Git unavailable). Real detected Godot 4.7.2 completed a temporary
project headless editor import via the generated shell alias, exit 0. Restricted
socket creation emitted Godot listener errors; this does not establish interactive
editor, GPU or gameplay compatibility. A live Codex app-server attempt disconnected
before initialization; an authenticated embedded tool call and live sandbox probe
could not be established here. These remain desktop release checks.

Real publisher downloads could not run because shell DNS/network access is
restricted. Optional installers have fixture validation, not live installation
certification. GTK display suite (`python3 -B tests/run_gtk.py`) could not start
because GTK3 `broadwayd` is absent (GTK4 Broadway is incompatible). A temporary Debian package built successfully using the existing unchanged launcher;
exact bundled sources, required runtime modules, Python syntax, amd64 ELF header
and desktop entry were verified. The temporary artifact was removed, leaving dist
unchanged. Fresh C compilation requires make/gcc, absent here; the standard package
validator also requires missing readelf. No build tool or dependency was installed.

Godot .NET/export templates, auto-update/uninstall, automatic system dependency
installation, independent signatures, automatic AppImage extraction and additional
platforms remain outside this beta change. Codex login remains separate: run the
wizard's shell-quoted executable plus `login`, follow native sign-in, then check
runtime and an authenticated embedded tool call. Studio does not infer sign-in
from executable discovery or read credentials.
