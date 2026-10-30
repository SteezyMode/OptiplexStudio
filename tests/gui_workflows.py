"""GTK integration driver under a private Broadway display. Fixtures only."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import zipfile
sys.path.insert(0, os.environ.get('STUDIO_TEST_LIB', str(Path(__file__).resolve().parents[1] / 'studio')))
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gtk, Gdk
import app
import project_client
import project_helper
import project_ui

workspace = tempfile.TemporaryDirectory(prefix='studio-gui-fixture-')
base = Path(workspace.name) / 'Godot'
base.mkdir()
for name in ('game-one', 'game-two'):
    project_helper.create_project(base, name)
project_helper.create_project(base, 'album', 'Studio')
project_ui.remember_project('game-two')
session_resumes = []
def transport(config, project, operation, progress=None, **fields):
    if operation == 'sessions':
        names = ('game-one', 'game-two') if fields.get('all_projects') else (project,)
        return {'sessions': [{'id': f'12345678-1234-1234-1234-{index:012d}', 'title': name + ' ' + title,
                              'project': name, 'cwd': str(base / name), 'createdAt': index, 'updatedAt': index}
                             for index, (name, title) in enumerate((n,t) for n in names for t in ('first','second'))], 'nextCursor': None}
    return project_helper.handle(dict(fields, project=project, operation=operation, version=1), base)
project_client.request = transport
app.core.projects = lambda config: [{'name': name, 'branch': 'main', 'dirty': True, 'commit': 'fixture'} for name in ('game-one', 'game-two')]
s = app.Studio()
s.config = {'projects_dir': str(base)}
phase = ['ready']
errors = []
started = time.monotonic()
snapshot = Path(workspace.name) / 'context.zip'


def later(function):
    def invoke():
        try: function()
        except Exception as exc: fail(exc)
        return False
    GLib.idle_add(invoke)


def fail(exc):
    errors.append(exc)
    for window in Gtk.Window.list_toplevels():
        window.destroy()
    s.quit()


def descendants(widget):
    yield widget
    if isinstance(widget, Gtk.Container):
        for child in widget.get_children():
            yield from descendants(child)


def drive():
    try:
        if time.monotonic() - started > 25:
            raise AssertionError('GUI workflow timed out at ' + phase[0])
        dialogs = [w for w in Gtk.Window.list_toplevels() if isinstance(w, Gtk.Dialog) and w.get_visible()]
        if phase[0] == 'ready' and getattr(s, 'rows', None) and not getattr(s, 'refreshing', True):
            assert s.combo.get_active_id() == 'game-two'
            assert GLib.get_prgname() == 'optiplex-studio'
            assert GLib.get_application_name() == 'OptiPlex Studio'
            assert s.get_application_id() == 'com.monumentrisk.OptiPlexStudio'
            if s.tray is not None and s.tray.is_embedded():
                assert s.tray.get_title() == 'OptiPlex Studio'
            assert s.active_label.get_text() == 'ACTIVE PROJECT: game-two'
            assert s.notebook.get_n_pages() == 2
            assert s.notebook.get_current_page() == 0
            assert [s.notebook.get_tab_label_text(s.notebook.get_nth_page(i)) for i in range(2)] == ['Studio', 'Project']
            captions = {w.get_label() for w in descendants(s.window) if isinstance(w, Gtk.Button)}
            assert {'Blockbench', 'LMMS', 'Krita', 'Blender', 'Import Assets', 'Share Project Context'} <= captions
            assert {'New Conversation', 'Resume Conversation', 'Run', 'Review Changes', 'Fix Godot Errors', 'Validate Project'} <= captions
            assert {'Godot · Edit', 'Play Game', 'Project Files', 'Import Assets'} <= captions
            assert not s.ai_advanced.get_expanded()
            assert not s.ai_run.get_sensitive()
            assert not s.ai_output_area.get_children()
            launch = s.open_embedded
            calls = []
            s.open_embedded = lambda *args, **kwargs: calls.append((args, kwargs, s.combo.get_active_id()))
            s.ai_prompt.get_buffer().set_text('  ')
            assert not s.ai_run.get_sensitive()
            s.ai_prompt.get_buffer().set_text('Review this project\nPreserve my work.')
            assert s.ai_run.get_sensitive()
            s.ai_run.clicked()
            assert calls == [((), {'prompt': 'Review this project\nPreserve my work.'}, 'game-two')]
            s.busy = True
            s.selection_changed(None)
            assert not s.ai_run.get_sensitive()
            assert not s.ai_prompt.get_sensitive()
            s.busy = False
            s.combo.set_active(-1)
            assert not s.ai_run.get_sensitive()
            s.combo.set_active_id('album')
            assert all(button.get_sensitive() for button in s.godot_buttons)
            assert all(button.get_sensitive() for button in s.project_buttons)
            s.ai_run.clicked()
            assert calls[-1][2] == 'album'
            s.open_embedded = launch
            s.ai_prompt.get_buffer().set_text('')
            s.combo.set_active_id('game-two')
            phase[0] = 'capture-main'
        elif phase[0] == 'capture-main':
            import cairo
            content=s.window.get_child()
            surface=cairo.ImageSurface(cairo.FORMAT_ARGB32,content.get_allocated_width(),content.get_allocated_height())
            content.draw(cairo.Context(surface))
            Path(workspace.name, 'qa').mkdir(parents=True,exist_ok=True)
            surface.write_to_png(str(Path(workspace.name, 'qa/project-workspace.png')))
            phase[0] = 'review'
            later(s.share_context)
        elif phase[0] == 'review':
            dialog = next((d for d in dialogs if 'Review project context' in d.get_title()), None)
            if dialog:
                tree = next(w for w in descendants(dialog) if isinstance(w, Gtk.TreeView))
                assert any(row[1] == 'GAME.md' and row[0] for row in tree.get_model())
                assert dialog.get_widget_for_response(4).get_sensitive()
                # Render the native dialog for visual QA without launching a browser.
                import cairo
                content = dialog.get_child()
                width, height = content.get_allocated_width(), content.get_allocated_height()
                surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
                content.draw(cairo.Context(surface))
                Path('build/qa').mkdir(parents=True, exist_ok=True)
                surface.write_to_png(str(Path(workspace.name, 'qa/snapshot-review.png')))
                phase[0] = 'save-picker'
                dialog.response(4)
        elif phase[0] == 'save-picker':
            dialog = next((d for d in dialogs if isinstance(d, Gtk.FileChooserDialog)), None)
            if dialog:
                dialog.set_current_folder(workspace.name)
                dialog.set_current_name('context.zip')
                phase[0] = 'saving'
                GLib.timeout_add(200, lambda: (dialog.response(Gtk.ResponseType.OK), False)[1])
        elif phase[0] == 'saving' and snapshot.exists() and not s.busy:
            with zipfile.ZipFile(snapshot) as archive:
                assert 'game-two/GAME.md' in archive.namelist()
                assert 'OVERVIEW.md' in archive.namelist()
            phase[0] = 'doc-choice'
            later(s.documents)
        elif phase[0] == 'doc-choice':
            dialog = next((d for d in dialogs if d.get_title() == 'game-two — Documentation'), None)
            if dialog:
                phase[0] = 'edit-doc'
                dialog.response(2)
        elif phase[0] == 'edit-doc':
            dialog = next((d for d in dialogs if d.get_title() == 'game-two / GAME.md'), None)
            if dialog:
                view = next(w for w in descendants(dialog) if isinstance(w, Gtk.TextView))
                view.get_buffer().set_text('# Edited fixture concept\n')
                phase[0] = 'doc-saved'
                dialog.response(Gtk.ResponseType.OK)
        elif phase[0] == 'doc-saved' and not s.busy:
            assert (base / 'game-two/GAME.md').read_text() == '# Edited fixture concept\n'
            assert (base / 'game-one/GAME.md').read_text() != '# Edited fixture concept\n'
            assert s.combo.get_active_id() == 'game-two'
            s.window.hide()
            s.activate()
            assert s.window.get_visible()
            phase[0] = 'sessions'
            s.open_embedded = lambda **kwargs: session_resumes.append(('resume',s.combo.get_active_id(),{'session_id':kwargs['identifier']}))
            s.action = lambda action, name=None, **kwargs: session_resumes.append((action,name,kwargs))
            later(s.session_browser)
        elif phase[0] == 'sessions':
            dialog = next((d for d in dialogs if d.get_title().startswith('Conversations')), None)
            if dialog:
                tree=next(w for w in descendants(dialog) if isinstance(w,Gtk.TreeView))
                if len(tree.get_model()) == 2:
                    scope=next(w for w in descendants(dialog) if isinstance(w,Gtk.CheckButton))
                    scope.set_active(True)
                    phase[0]='all-sessions'
        elif phase[0] == 'all-sessions':
            dialog=next((d for d in dialogs if d.get_title().startswith('Conversations')),None)
            if dialog:
                tree=next(w for w in descendants(dialog) if isinstance(w,Gtk.TreeView))
                if len(tree.get_model()) == 4:
                    search=next(w for w in descendants(dialog) if isinstance(w,Gtk.SearchEntry))
                    search.set_text('game-one second')
                    search.emit('search-changed')
                    assert len(tree.get_model()) == 1
                    tree.get_selection().select_path(Gtk.TreePath.new_from_indices([0]))
                    assert dialog.get_widget_for_response(Gtk.ResponseType.OK).get_sensitive()
                    phase[0]='session-resumed'
                    dialog.response(Gtk.ResponseType.OK)
        elif phase[0] == 'session-resumed':
            assert session_resumes == [('resume','game-one',{'session_id':'12345678-1234-1234-1234-000000000001'})]
            assert s.combo.get_active_id() == 'game-one'
            phase[0]='new-template'
            later(lambda: s.create_project(None))
        elif phase[0] == 'new-template':
            dialog=next((d for d in dialogs if d.get_title() == 'New project'),None)
            if dialog:
                entry=next(w for w in descendants(dialog) if isinstance(w,Gtk.Entry))
                entry.set_text('new-album')
                phase[0]='created'
                dialog.response(Gtk.ResponseType.OK)
        elif phase[0] == 'created':
            assert session_resumes[-1] == ('new','new-album',{})
            print('GTK integration passed: local project creation, session search/all-project filtering/UUID resume, actual launcher names, remembered selection, native snapshot review/save ZIP, documentation edit/conflict token, project isolation and restoration.')
            s.quit()
            return False
    except Exception as exc:
        fail(exc)
        return False
    return True

GLib.timeout_add(100, drive)
s.run(None)
workspace.cleanup()
if errors:
    raise errors[0]
