# Project-first conversations and native integration

Status: accepted direction; implementation scope recorded below. 2026-10-19.

Projects are Studio's organizing concept. The active Project owns new conversations,
resume actions, editable AI memory, sources and native application handoffs. A
conversation is Codex history associated with a Project, not a replacement Project.
Global discovery must select the owning Project before resume. Unknown ownership
stays unassigned and cannot resume through Studio. Original Codex histories remain
untouched; metadata is read through app-server. Resume must validate ownership in
application logic, including direct callers, and fail closed when metadata is unavailable.

Use an additive project UUID sidecar for identity without rewriting existing project
metadata. Persist verified conversation associations separately in each Project.
Only existing recognized Projects and exact canonical working directories or their
children establish ownership; traversal, symlinks, conflicting identities and ambiguous
associations must not guess. Path aliases across machines require explicit future
registration. This source repository is application source, not a Godot game;
only a real project.godot establishes a Godot project.

AI_MEMORY.md is editable project-owned context, not a transcript or automatic learned
memory. New Codex launches explicitly receive its current contents in the initial
prompt. Existing conversations retain their original history. Writes use existing
bounded, symlink-resistant, conflict-checked document operations. Keep titles, dates,
Project names and active Project visible; hide paths and UUIDs in routine UI.

Native roadmap, in priority order:

1. P0: project-scoped conversations, ownership checks, global discovery, memory and
   regression coverage. Preserve --no-daemon in every native Codex launch.
2. P1: one first-run setup wizard for Godot, Blender, Blockbench, LMMS, Krita and
   Codex. Inventory existing persistent installs first; use current executable
   settings, PATH and ~/.local/bin discovery. Let users browse for a persistent
   native executable and retain settings. Report Ready, Missing or Needs attention
   per tool, offer recheck and skip, and reopen from Settings. No Flatpak or Wolf
   dependency. Do not download anything until sources, versions, platform support,
   checksums and user-selected destinations have been verified. Codex authentication
   stays in its native flow; do not copy credentials. Never overwrite installations.
3. P1: native adapters open selected editable source files, track exports and handoffs
   within the Project; Godot only for Godot projects. Verify each adapter with real
   installed versions before claiming integration.
4. P2: shared runtime/task ownership and reconnect per ADR-001, explicit path aliases,
   duplicate-project identity resolution, native application version/capability probes
   and conflict-aware simultaneous frontend work.

P1 now adds a first-run Tools & Setup flow, passive installation inventory, native
executable selection, persistent directory discovery and optional VSCodium Open
Current Project. Settings reopens setup; users can recheck or skip without installs.
The validated project-first conversation/document layer is preserved. Verified
installers, runtime capability probes, shared running-process reconnection and
richer native file handoffs remain roadmap work. Future VSCodium Codex change
review must retain project ownership and explicit review decisions. Krita scripting
and LMMS scaling remain compatibility observations, not fixes in this pass. Existing services and optional remote workflows are
not migrated or reconfigured.

## Validation for this implementation

- `python3 -B -m unittest discover -s tests -v`: 153 tests, successful;
  four skipped (three require Git; one requires Unix sockets prohibited here).
- Python compilation of `studio` and `tests`: successful, bytecode directed to /tmp.
- Tests cover real fixture app-server stdio, pagination, project ownership rejection,
  direct UI cross-project rejection, rename persistence, conflicting associations,
  duplicate UUIDs, unassigned paths, preserved history bytes, memory conflict checks,
  explicit memory context and the native terminal --no-daemon argument.
- GTK fixture runner attempted but blocked: GTK3 broadwayd is unavailable. GUI
  fixtures have updated conversation labels and retain global-switch-before-resume
  checks. Actual native Codex authentication/interactive resume and six creative
  applications need workstation verification. No real user sessions were launched.
- Native build/package validation unavailable here (make/gcc absent); existing
  build and distribution artifacts were preserved. Git is also absent, so no Git
  diff/status verification was possible. No commits, pushes or merges were made.

## P1 native setup validation (2026-10-19)

- Full unittest suite: 158 tests, successful, four skipped (existing Git/socket
  environment restrictions). Added passive discovery, versioned native layouts,
  extracted AppRun, invalid override, directory validation and VSCodium project
  argv coverage. The legacy missing-tool fixture now isolates persistent roots.
- Compilation of studio and tests passed with bytecode confined to /tmp.
- Passive inventory found Godot, Blender, Blockbench, LMMS, Krita and Codex at the
  existing test installations; VSCodium was Missing. No application was executed.
- GTK runner blocked by missing broadwayd. Interactive setup and real application
  launches still require workstation verification. make/gcc and Git are absent,
  so native build/package and Git diff checks were unavailable. Existing artifacts
  were preserved; no commit, push, merge, download or installation was performed.

## Embedded App Server milestone (2026-10-19)

Implemented in source: a conversation panel in the existing GTK3 AI Workspace,
using a dedicated native `codex app-server --listen stdio://` process per open
view. New threads are persistent; resume first verifies Studio ownership and reads
server metadata before resuming. Returned IDs and cwd are checked. Project UUIDs
and additive associations remain the ownership boundary. AI_MEMORY.md is supplied
only to new threads using the existing bounded native-launch context policy.
There is no rollout/SQLite editing or automatic transcript/memory rewriting.

The panel supports send, streamed agent text and command output, tool lifecycle,
interrupt, reconnect, and a preserved External Terminal fallback. Run and task
presets start a new thread and submit the selected prompt after connection. Read-only
sandbox, `untrusted` approval policy and `approvalsReviewer: user` override unsafe
inherited defaults. Command and file-change approval requests offer Deny or Approve
once; closing an approval denies it. No session/policy approval caches are accepted.
Unknown request types return an RPC error, rather than approving or executing them.
File changes show the streamed patch item alongside the request; approval is
disabled if patch details are unavailable. Permission grants and interactive
tool-input requests require the terminal fallback.
Read-only operations permitted by Codex's untrusted policy may run without an
approval request; Studio never automatically answers an approval with acceptance.

RPC reads and writes run outside GTK; GLib dispatches view changes. Disconnects,
malformed/oversized frames and request timeouts release waiters and invalidate
approvals. Closing a panel or shutting down terminates and asynchronously reaps its
owned server only. Reconnect re-verifies the original thread and project identity;
it never replays an uncertain message. Users should review resumed history before
resubmitting after an ambiguous failure. The rendered output is bounded to 300,000
characters; Codex retains the actual persistent history. One panel is open at a time.
Renamed projects retain identity associations, but a thread whose recorded cwd
no longer matches is rejected by the embedded client pending explicit path recovery.

### Next separate milestone: historical session recovery

No historical unassigned sessions are claimed by this implementation. Existing
verified canonical-cwd and saved-association rules are unchanged. Unassigned rows
remain visible in All Projects and cannot be resumed through Studio. Build a
separate explicit, reviewable recovery flow for old paths, moved projects and
ambiguous identities; never infer ownership from titles or bulk-assign histories.
Shared live runtime ownership and cross-frontend reconnect also remain deferred.

### Validation status

- Installed Codex: `codex-cli 0.163.0`, discovered at `~/.local/bin/codex`.
  Inspected `app-server --help` and generated JSON Schema into `/tmp`, including
  initialize, thread/read/start/resume, turn/start/interrupt and approval decisions.
  Official protocol reference: https://developers.openai.com/codex/app-server.
- Full suite with the existing Git executable on PATH: 177 tests run, 176 passed,
  one skipped (Unix sockets prohibited). The default-PATH run also passed, with
  three additional Git-dependent skips. Two existing session fixtures initially
  selected the real Codex when PATH changed; they now explicitly select their
  fixture executable, and the complete rerun passed.
  New deterministic stdio fixtures cover RPC, explicit approval, unknown requests,
  malformed JSON, disconnect and startup failure. Tests also cover project
  isolation, memory reuse, persistent metadata, cwd rejection, identity changes,
  fast turn completion, GTK handler cleanup and default-deny approval behavior.
- Python compilation and `git diff --check` passed. GTK fixture runner attempted:
  blocked by missing GTK3 `broadwayd`. Added display-backed embedded panel fixture
  for that runner; live layout and interaction at 1024x768 remain unverified here.
- A native read-only startup/initialize probe failed: installed App Server exits
  with `Read-only file system` under this environment's restricted home. No real
  thread was created and no authenticated turn or real tool approval was tested.
  Live streaming, sandbox approval behavior, persistence across actual native
  restarts and workstation shutdown still need workstation acceptance testing.
- No packages installed, user projects migrated, sessions edited, services changed,
  deployment performed, or commits/pushes/merges made. This is source implementation,
  not a claim that the existing Wolf launcher or installed GUI has been repaired.
