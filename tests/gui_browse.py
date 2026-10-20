"""Exercise packaged widgets/callbacks and native folder chooser on local fixtures."""
import os,sys,tempfile,time
from pathlib import Path
sys.path.insert(0,os.environ.get('STUDIO_TEST_LIB',str(Path(__file__).resolve().parents[1]/'studio')))
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GLib,Gio
import app,project_client,project_helper,file_browser,native_tools

fixture=tempfile.TemporaryDirectory(prefix='studio-browser-fixture-')
base=Path(fixture.name)
project_helper.create_project(base,'game')
project_helper.create_project(base,'other')
session_id='11111111-1111-4111-8111-111111111111'
other_session_id='22222222-2222-4222-8222-222222222222'
def request(config,project,operation,progress=None,**fields):
    if operation=='sessions':
        rows=[{'id':session_id,'title':'Fixture conversation','project':'game',
               'cwd':str(base/'game'),'updatedAt':1}]
        if fields.get('all_projects'):
            rows.append({'id':other_session_id,'title':'Other project conversation','project':'other',
                         'cwd':str(base/'other'),'updatedAt':2})
        return {'sessions':rows, 'nextCursor':None}
    return project_helper.handle(dict(fields,version=1,project=project,operation=operation),base)
project_client.request=request
app.core.projects=lambda config:[{'name':name,'type':'Godot'} for name in ('game','other')]
s=app.Studio();s.config={'projects_dir':str(base)}
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
def button(caption,root=None):
    matches=[w for w in children(root or s.window) if isinstance(w,Gtk.Button) and w.get_label()==caption]
    assert len(matches)==1, f'Expected one {caption!r} button, found {len(matches)}'
    return matches[0]
ADVANCED_ACTIONS=('Find Conversations','Explain Project','Copy ChatGPT Brief','Open ChatGPT')
def check_advanced(expanded):
    expander=s.ai_advanced
    assert expander.get_expanded()==expanded
    content=expander.get_child()
    assert content is not None and content.get_parent()==expander
    for name in ADVANCED_ACTIONS:
        control=button(name)
        assert control.is_ancestor(content), f'{name} must be inside More actions'
        assert control.get_visible() and control.is_sensitive(),name
        if expanded:
            assert control.get_mapped(),name
    # GTK3's expander excludes its child from layout/drawing when collapsed,
    # but descendants can retain their mapped flags (including after show_all).
    # Check the layout it exposes instead: expansion must reserve the content's
    # height, and collapse must restore the original header-only height.
    minimum,natural=expander.get_preferred_height()
    if expanded:
        child_minimum=content.get_preferred_height()[0]
        assert child_minimum>0
        assert minimum>=collapsed_height[0]+child_minimum
        assert natural>collapsed_height[1]
    else:
        assert (minimum,natural)==collapsed_height
    return minimum

def click(caption):
    control=button(caption)
    assert control.get_mapped() and control.is_sensitive(),caption
    ancestor=control.get_parent()
    while ancestor is not None:
        if isinstance(ancestor,Gtk.Expander):
            assert ancestor.get_expanded(), f'{caption} is inside a collapsed expander'
        ancestor=ancestor.get_parent()
    control.clicked()
def later(callback):
    GLib.idle_add(lambda:(callback(),False)[1])
def drive():
    global collapsed_height
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
                        dialog.select_file(Gio.File.new_for_path(str(base/'game/GAME.md')))
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
            native_tools.run_action=lambda config,action,name,**kwargs:actions.append((action,name,kwargs)) or 'Fixture action routed'
            phase[0]='ai-visible'
        elif phase[0]=='ai-visible':
            for name in ('New Conversation','Resume Conversation','Review Changes','Fix Godot Errors','Validate Project'):
                control=button(name)
                assert control.get_mapped() and control.is_sensitive(),name
            assert s.ai_prompt.get_mapped() and s.ai_prompt.is_sensitive()
            assert button('Run').get_mapped() and not button('Run').is_sensitive()
            assert s.ai_advanced.get_label()=='More actions' and s.ai_advanced.get_mapped()
            assert not s.ai_advanced.get_expanded()
            collapsed_height=tuple(s.ai_advanced.get_preferred_height())
            check_advanced(False)
            phase[0]='new-codex';later(lambda:click('New Conversation'))
        elif phase[0]=='new-codex' and not s.busy:
            assert len(actions)==1 and actions[-1][:2]==('code','game')
            assert 'prompt' not in actions[-1][2] and 'session_id' not in actions[-1][2]
            phase[0]='session-dialog';later(lambda:click('Resume Conversation'))
        elif phase[0]=='session-dialog':
            dialog=next((w for w in dialogs if w.get_title()=='Conversations — game'),None)
            if dialog:
                tree=next(w for w in children(dialog) if isinstance(w,Gtk.TreeView))
                if len(tree.get_model()):
                    assert len(actions)==1, 'Opening the browser must not launch Codex'
                    assert len(tree.get_model())==1 and tree.get_model()[0][3]==session_id
                    resume=dialog.get_widget_for_response(Gtk.ResponseType.OK)
                    tree.get_selection().unselect_all()
                    assert resume.get_mapped() and not resume.is_sensitive()
                    tree.get_selection().select_path(Gtk.TreePath.new_from_string('0'))
                    assert resume.is_sensitive()
                    phase[0]='resumed';resume.clicked()
        elif phase[0]=='resumed' and not s.busy:
            assert len(actions)==2 and actions[-1][:2]==('resume','game')
            assert actions[-1][2]['session_id']==session_id
            s.ai_prompt.get_buffer().set_text('   \n')
            assert not button('Run').is_sensitive()
            s.ai_prompt.get_buffer().set_text('Inspect the fixture project.\nKeep its assets intact.')
            assert button('Run').is_sensitive()
            phase[0]='custom';later(lambda:click('Run'))
        elif phase[0]=='custom' and not s.busy:
            assert len(actions)==3 and actions[-1][:2]==('code','game')
            assert actions[-1][2]['prompt']=='Inspect the fixture project.\nKeep its assets intact.'
            assert button('Run').is_sensitive(), 'Run must be restored after completion'
            s.ai_prompt.get_buffer().set_text('')
            assert not button('Run').is_sensitive()
            phase[0]='preset-0';later(lambda:click('Review Changes'))
        elif phase[0].startswith('preset-') and not s.busy:
            index=int(phase[0].split('-')[1])
            presets=('Review Changes','Fix Godot Errors','Validate Project')
            assert len(actions)==4+index and actions[-1][:2]==('code','game')
            assert actions[-1][2]['prompt']==app.core.CODEX_TASKS[presets[index]]
            if index<2:
                phase[0]=f'preset-{index+1}';later(lambda:click(presets[index+1]))
            else:
                assert not s.ai_advanced.get_expanded()
                s.ai_advanced.activate()
                phase[0]='advanced-visible'
        elif phase[0]=='advanced-visible':
            minimum=check_advanced(True)
            if s.ai_advanced.get_allocated_height()<minimum:
                return True  # Allow GTK's queued resize to finish before clicking.
            phase[0]='picker';later(lambda:click('Find Conversations'))
        elif phase[0]=='picker' and not s.busy:
            dialog=next((w for w in dialogs if w.get_title()=='Conversations — game'),None)
            if dialog:
                scope=next(w for w in children(dialog) if isinstance(w,Gtk.CheckButton))
                scope.set_active(True)
                phase[0]='all-projects'
        elif phase[0]=='all-projects':
            dialog=next((w for w in dialogs if w.get_title()=='Conversations — game'),None)
            if dialog:
                tree=next(w for w in children(dialog) if isinstance(w,Gtk.TreeView))
                if len(tree.get_model())==2:
                    assert {tree.get_model()[i][1] for i in range(2)}=={'game','other'}
                    tree.get_selection().select_path(Gtk.TreePath.new_from_string('0'))
                    phase[0]='global-resumed';dialog.response(Gtk.ResponseType.OK)
        elif phase[0]=='global-resumed' and not s.busy:
            print('GLOBAL RESUME DEBUG:', repr(actions), 'ACTIVE:', s.combo.get_active_id(), 'STATUS:', s.status.get_text(), flush=True)
            assert len(actions)==7 and actions[-1][:2]==('resume','other')
            assert actions[-1][2]['session_id']==other_session_id
            assert s.combo.get_active_id()=='other', 'Global resume must switch to the owning Project first'
            # Direct callers must not bypass the active-project ownership check.
            s.combo.set_active_id('game')
            before=len(actions)
            s.action('resume','other',session_id=other_session_id)
            assert len(actions)==before
            assert 'owning Project' in s.status.get_text()
            phase[0]='explain';later(lambda:click('Explain Project'))
        elif phase[0]=='explain' and not s.busy:
            assert len(actions)==8 and actions[-1][:2]==('code','game')
            assert actions[-1][2]['prompt']==app.core.CODEX_TASKS['Explain Project']
            s.ai_advanced.activate()
            phase[0]='collapsed'
        elif phase[0]=='collapsed':
            check_advanced(False)
            if s.ai_advanced.get_allocated_height()>collapsed_height[1]:
                return True  # Collapse must also reclaim the space on screen.
            assert button('New Conversation').get_mapped() and button('Resume Conversation').get_mapped()
            print('GTK browser/AI checks passed: native folders and local download; project-scoped conversation resume, all-project owner switching and ownership enforcement, custom prompt Run, all presets, and expanded/collapsed More actions route the selected project.')
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
