from pathlib import Path

def replace_once(path, old, new):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"{path}: needed one occurrence, saw {count}: {old[:100]!r}")
    p.write_text(s.replace(old, new, 1), encoding="utf-8")

# PhotoCraft's normalizer had been changing PageUp -> Pageup.
# egui::Key::from_name("Pageup") fails, making the displayed shortcut non-functional.
replace_once(
    "crates/engine/src/prefs.rs",
    '''fn capitalize(s: &str) -> String {
    let mut c = s.chars();
''',
    '''fn capitalize(s: &str) -> String {
    // Keep egui's mixed-case key names intact so saved assignments round-trip.
    // Before this, PageUp became Pageup and was unparseable by egui.
    if let Some(name) = match s.to_ascii_lowercase().as_str() {
        "pageup" => Some("PageUp"),
        "pagedown" => Some("PageDown"),
        "arrowup" => Some("ArrowUp"),
        "arrowdown" => Some("ArrowDown"),
        "arrowleft" => Some("ArrowLeft"),
        "arrowright" => Some("ArrowRight"),
        "intlbackslash" => Some("IntlBackslash"),
        "openbracket" => Some("OpenBracket"),
        "closebracket" => Some("CloseBracket"),
        "opencurlybracket" => Some("OpenCurlyBracket"),
        "closecurlybracket" => Some("CloseCurlyBracket"),
        _ => None,
    } {
        return name.to_string();
    }
    let mut c = s.chars();
'''
)

# Backward compatibility: prefs already saved by custom.8 or .9 spell Pageup.
replace_once(
    "crates/ui-egui/src/shortcuts.rs",
    '''                key = Key::from_name(k).or(match k {
                    "=" => Some(Key::Equals),
''',
    '''                key = Key::from_name(k).or(match k.to_ascii_lowercase().as_str() {
                    "pageup" => Some(Key::PageUp),
                    "pagedown" => Some(Key::PageDown),
                    "arrowup" => Some(Key::ArrowUp),
                    "arrowdown" => Some(Key::ArrowDown),
                    "arrowleft" => Some(Key::ArrowLeft),
                    "arrowright" => Some(Key::ArrowRight),
                    "intlbackslash" => Some(Key::IntlBackslash),
                    "openbracket" => Some(Key::OpenBracket),
                    "closebracket" => Some(Key::CloseBracket),
                    "opencurlybracket" => Some(Key::OpenCurlyBracket),
                    "closecurlybracket" => Some(Key::CloseCurlyBracket),
                    "=" => Some(Key::Equals),
'''
)

# A focused options-bar widget consumes navigation keys such as PageUp.
# The user's explicit Smudge toggle assignment must win unless a text field owns the key.
replace_once(
    "crates/ui-egui/src/shortcut_dispatch.rs",
    '''        bindings(app).into_iter().filter(|(id, sc)| focus.allows(sc) && !(editing && TEXT_OWNED.contains(&id.as_str()))).collect();
''',
    '''        bindings(app)
            .into_iter()
            .filter(|(id, sc)| {
                let smudge_control = id == "ui.smudgeToggleStrength"
                    && app.active_tool() == crate::state::Tool::Smudge
                    && matches!(focus, Focus::Widget | Focus::DeletingWidget);
                (focus.allows(sc) || smudge_control)
                    && !(editing && TEXT_OWNED.contains(&id.as_str()))
            })
            .collect();
'''
)

# Regression test: genuine input event from the previously saved string,
# including after an options-bar widget has focus.
replace_once(
    "crates/ui-egui/src/shortcuts.rs",
    '''    #[test]
    fn keys_match_like_photoshop() {
''',
    '''    #[test]
    fn smudge_strength_pageup_shortcut_survives_saved_preferences_and_dispatches() {
        use crate::shortcut_dispatch::{Focus, dispatch_pressed};
        assert_eq!(photocraft_engine::prefs::normalize_shortcut("PageUp").as_deref(), Some("PageUp"));
        assert_eq!(photocraft_engine::prefs::normalize_shortcut("Pageup").as_deref(), Some("PageUp"));
        assert_eq!(parse("PageUp").unwrap().logical_key, Key::PageUp);
        assert_eq!(parse("Pageup").unwrap().logical_key, Key::PageUp);

        let mut app = PhotocraftApp::new(photocraft_engine::Session::new(), Default::default());
        app.run("file.new", serde_json::json!({"width": 100, "height": 100})).unwrap();
        app.ui.tool = Tool::Smudge;
        app.ui.tool_options.strength = 18.0;
        app.session.prefs.edit(|p| {
            p.shortcuts.insert("ui.smudgeToggleStrength".into(), "Pageup".into());
            p.workflow_memory.smudge_low_strength = 18.0;
            p.workflow_memory.smudge_high_strength = 70.0;
        });
        assert!(crate::menus::is_enabled(&app, "ui.smudgeToggleStrength"));
        let ctx = egui::Context::default();
        let press = |app: &mut PhotocraftApp, focus| {
            ctx.begin_pass(egui::RawInput {
                events: vec![
                    egui::Event::Key {
                        key: Key::PageUp,
                        physical_key: None,
                        pressed: true,
                        repeat: false,
                        modifiers: Modifiers::NONE,
                    }
                ],
                ..Default::default()
            });
            assert!(dispatch_pressed(app, &ctx, focus, false), "PageUp was not dispatched");
            ctx.end_pass().textures_delta.clear();
        };
        press(&mut app, Focus::None);
        assert_eq!(app.ui.tool_options.strength, 70.0);
        press(&mut app, Focus::Widget);
        assert_eq!(app.ui.tool_options.strength, 18.0);
    }

    #[test]
    fn keys_match_like_photoshop() {
'''
)
print("custom.10 patched: PageUp/PageDown parser and prefs round-trip, Smudge focus override, regression test.")
