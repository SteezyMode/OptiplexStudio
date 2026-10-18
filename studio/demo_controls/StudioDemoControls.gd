extends CanvasLayer
# OptiPlex Studio: managed demo exit controls
## OptiPlex Studio's universal exit/pause controls for disposable Godot demos.
## Injected only into registered Studio experiment projects, never production games.
## F10: always quit. Esc: pause menu. Works with captured mouse input.

var _overlay: ColorRect
var _menu_open: bool = false
var _was_paused: bool = false
var _old_mouse_mode: Input.MouseMode = Input.MOUSE_MODE_VISIBLE

func _ready() -> void:
    process_mode = Node.PROCESS_MODE_ALWAYS
    layer = 100
    _build_menu()
    call_deferred("_ensure_windowed")

func _ensure_windowed() -> void:
    if DisplayServer.get_name() == "headless":
        return
    DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
    DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_BORDERLESS, false)
    DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_RESIZE_DISABLED, false)
    var current: Vector2i = DisplayServer.window_get_size()
    if current.x > 960 or current.y > 540:
        var factor: float = minf(960.0 / maxf(1.0, float(current.x)), 540.0 / maxf(1.0, float(current.y)))
        DisplayServer.window_set_size(Vector2i(maxi(320, int(current.x * factor)), maxi(240, int(current.y * factor))))

func _input(event: InputEvent) -> void:
    var key: InputEventKey = event as InputEventKey
    if key == null or not key.pressed or key.echo:
        return
    if key.keycode == KEY_F10 or key.physical_keycode == KEY_F10:
        get_viewport().set_input_as_handled()
        _quit_demo()
    elif key.keycode == KEY_ESCAPE or key.physical_keycode == KEY_ESCAPE:
        get_viewport().set_input_as_handled()
        if _menu_open:
            _resume()
        else:
            _pause()

func _pause() -> void:
    if _menu_open:
        return
    _menu_open = true
    _was_paused = get_tree().paused
    _old_mouse_mode = Input.mouse_mode
    Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
    get_tree().paused = true
    _overlay.show()

func _resume() -> void:
    if not _menu_open:
        return
    _overlay.hide()
    _menu_open = false
    get_tree().paused = _was_paused
    Input.mouse_mode = _old_mouse_mode

func _restart() -> void:
    _resume()
    if get_tree().current_scene != null:
        get_tree().reload_current_scene()

func _quit_demo() -> void:
    Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
    get_tree().paused = false
    get_tree().quit()

func _build_menu() -> void:
    _overlay = ColorRect.new()
    _overlay.name = "StudioDemoExitOverlay"
    _overlay.color = Color(0.0, 0.0, 0.0, 0.77)
    _overlay.mouse_filter = Control.MOUSE_FILTER_STOP
    add_child(_overlay)
    _overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

    var center: CenterContainer = CenterContainer.new()
    _overlay.add_child(center)
    center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

    var panel: PanelContainer = PanelContainer.new()
    panel.custom_minimum_size = Vector2(300, 225)
    center.add_child(panel)

    var vbox: VBoxContainer = VBoxContainer.new()
    vbox.add_theme_constant_override("separation", 10)
    panel.add_child(vbox)

    var title: Label = Label.new()
    title.text = "Studio Demo Paused"
    title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
    vbox.add_child(title)

    var hint: Label = Label.new()
    hint.text = "Esc: resume / menu     F10: quit"
    hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
    vbox.add_child(hint)

    _add_button(vbox, "Resume", _resume)
    _add_button(vbox, "Restart Demo", _restart)
    _add_button(vbox, "Quit to Desktop", _quit_demo)
    _overlay.hide()

func _add_button(parent: VBoxContainer, caption: String, action: Callable) -> void:
    var button: Button = Button.new()
    button.text = caption
    button.custom_minimum_size.y = 34
    button.pressed.connect(action)
    parent.add_child(button)
