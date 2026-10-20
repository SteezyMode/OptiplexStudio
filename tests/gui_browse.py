"""Exercise packaged widgets/callbacks and native folder chooser on local fixtures."""
import os,sys,tempfile,time
from pathlib import Path
sys.path.insert(0,os.environ.get('STUDIO_TEST_LIB',str(Path(__file__).resolve().parents[1]/'studio')))
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GLib,Gio
import app,project_client,project_helper,file_browser

fixture=tempfile.TemporaryDirectory(prefix='studio-browser-fixture-')
base=Path(fixture.name)
project_helper.create_project(base,'game')
project_client.request=lambda config,project,operation,progress=None,**fields: project_helper.handle(dict(fields,version=1,project=project,operation=operation),base)
app.core.projects=lambda config:[{'name':'game','type':'Godot'}]
s=app.Studio();s.config={'mode':'local'}
phase=['ready'];errors=[];actions=[];started=time.monotonic()
original_init=file_browser.RemoteFolder.__init__
def init(self,parent,uri,finished,status):
    original_init(self,parent,uri,finished,status)
    self.file=Gio.File.new_for_path(str(base/'game'/('assets' if uri.endswith('/assets') else '')))
file_browser.RemoteFolder.__init__=init
file_browser.RemoteFolder.open=lambda self:self.native_browser()
def children(widget):
    yield widget
    if isinstance(widget,Gtk.Container):
        for child in widget.get_children():yield from children(child)
def click(caption):
    button=next(w for w in children(s.window) if isinstance(w,Gtk.Button) and w.get_label()==caption)
    assert button.get_sensitive(),caption
    button.clicked()
def later(callback):
    GLib.idle_add(lambda:(callback(),False)[1])
def drive():
    try:
        assert time.monotonic()-started<25,'Timed out: '+phase[0]
        dialogs=[w for w in Gtk.Window.list_toplevels() if isinstance(w,Gtk.Dialog) and w.get_visible()]
        if phase[0]=='ready' and s.rows and not s.refreshing:
            phase[0]='files';later(lambda:click('Project Files'))
        elif phase[0] in ('files','assets'):
            dialog=next((w for w in dialogs if isinstance(w,Gtk.FileChooserDialog)),None)
            if dialog and dialog.get_current_folder_file():
                expected=base/'game'/('assets' if phase[0]=='assets' else '')
                if dialog.get_current_folder_file().get_path()==str(expected):
                    if phase[0]=='files':
                        dialog.set_filename(str(base/'game/GAME.md'))
                        phase[0]='select-download'
                    else:
                        phase[0]='ai-start'
                        dialog.response(Gtk.ResponseType.CLOSE)
        elif phase[0]=='select-download':
            dialog=next((w for w in dialogs if isinstance(w,Gtk.FileChooserDialog)),None)
            if dialog and dialog.get_file() and dialog.get_file().get_basename()=='GAME.md':
                phase[0]='save-copy'
                dialog.response(Gtk.ResponseType.OK)
        elif phase[0]=='save-copy':
            dialog=next((w for w in dialogs if w.get_title()=='Save Local Copy'),None)
            if dialog:
                dialog.set_current_folder(str(base))
                dialog.set_current_name('downloaded-GAME.md')
                phase[0]='downloaded'
                GLib.timeout_add(200,lambda:(dialog.response(Gtk.ResponseType.OK),False)[1])
        elif phase[0]=='downloaded' and (base/'downloaded-GAME.md').exists() and not any(w.get_title()=='Downloading project file' for w in dialogs):
            assert (base/'downloaded-GAME.md').read_bytes()==(base/'game/GAME.md').read_bytes()
            dialog=next((w for w in dialogs if isinstance(w,Gtk.FileChooserDialog) and w.get_title().startswith('Project Files')),None)
            if dialog:
                phase[0]='assets-start';dialog.response(Gtk.ResponseType.CLOSE)
        elif phase[0]=='assets-start' and not s.busy:
            phase[0]='assets';later(lambda:click('Browse Assets'))
        elif phase[0]=='ai-start' and not s.busy:
            notebook=next(w for w in children(s.window) if isinstance(w,Gtk.Notebook));notebook.set_current_page(1)
            app.core.run_action=lambda config,action,name,**kwargs:actions.append((action,name,kwargs)) or 'Fixture action routed'
            phase[0]='ai-visible'
        elif phase[0]=='ai-visible':
            names=('Open Codex Workspace','Resume Session…','Codex Conversation Picker','Review Changes','Explain Project','Fix Godot Errors','Validate Project')
            for name in names:
                button=next(w for w in children(s.window) if isinstance(w,Gtk.Button) and w.get_label()==name)
                assert button.get_mapped() and button.get_sensitive(),name
            phase[0]='new-codex';later(lambda:click('Open Codex Workspace'))
        elif phase[0]=='new-codex' and not s.busy:
            assert actions[-1][:2]==('code','game')
            phase[0]='review';later(lambda:click('Review Changes'))
        elif phase[0]=='review' and not s.busy:
            assert actions[-1][2]['prompt']==app.core.CODEX_TASKS['Review Changes']
            print('Packaged GTK browser/AI checks passed: actual Project Files and Browse Assets clicks display native folder contents and save a local copy; AI controls are mapped, sensitive and route the selected project.')
            s.quit();return False
    except Exception as exc:
        errors.append(exc)
        for dialog in Gtk.Window.list_toplevels():dialog.destroy()
        s.quit();return False
    return True
GLib.timeout_add(100,drive)
s.run(None)
fixture.cleanup()
if errors:raise errors[0]
