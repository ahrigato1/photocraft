from pathlib import Path

ROOT = Path(".")

def replace_once(path, old, new):
    p = ROOT / path
    s = p.read_text(encoding="utf-8")
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"{path}: expected 1 occurrence, got {n}: {old[:70]!r}")
    p.write_text(s.replace(old, new, 1), encoding="utf-8")

# Register this as a real UI command so Edit > Keyboard Shortcuts shows it,
# persists its assignment, checks for collisions, and dispatches it centrally.
replace_once(
    "crates/ui-egui/src/menus.rs",
    '    ("ui.symmetryTransform", "Transform Symmetry", &[], None),\n',
    '    ("ui.symmetryTransform", "Transform Symmetry", &[], None),\n'
    '    ("ui.smudgeToggleStrength", "Toggle Smudge Strength Preset", &["Edit", "Tools"], None),\n'
)
replace_once(
    "crates/ui-egui/src/menus.rs",
    '''    if id == "ui.symmetryTransform" {
        return crate::symmetry_ui::begin(app).map(|_| Value::Null);
    }
''',
    '''    if id == "ui.smudgeToggleStrength" {
        if app.ui.tool != crate::state::Tool::Smudge {
            return Ok(Value::Null);
        }
        let memory = &app.session.prefs().workflow_memory;
        let low = memory.smudge_low_strength.clamp(1.0, 100.0);
        let high = memory.smudge_high_strength.clamp(1.0, 100.0);
        let current = app.ui.tool_options.strength;
        app.ui.tool_options.strength =
            if (current - low).abs() <= (current - high).abs() { high } else { low };
        return Ok(json!({"strength": app.ui.tool_options.strength}));
    }
    if id == "ui.symmetryTransform" {
        return crate::symmetry_ui::begin(app).map(|_| Value::Null);
    }
'''
)

# The shortcut editor includes UI commands with a menu path, even with no default
# shortcut; keep the command in the list and expose it via search.
# Remove the fragile TextEdit inside an egui menu (menu closes on click).
p = "crates/ui-egui/src/retouch_ui.rs"
s = (ROOT/p).read_text(encoding="utf-8")
old = '''                let toggle_key = memory.smudge_toggle_shortcut.clone();
                if !toggle_key.is_empty()
                    && !ui.ctx().egui_wants_keyboard_input()
                    && let Some(shortcut) = crate::shortcuts::parse(&toggle_key)
                    && crate::shortcuts::consume(ui.ctx(), &shortcut)
                {
                    // Whichever slot is currently closer is the one we leave.
                    o.strength = if (o.strength - low).abs() <= (o.strength - high).abs() { high } else { low };
                }
'''
if s.count(old) != 1:
    raise SystemExit("retouch_ui: cannot locate legacy local shortcut handler")
s = s.replace(old, '', 1)
old = '''                    ui.label("Toggle shortcut (e.g. F6 or Ctrl+Alt+M):");
                    let mut key = app.session.prefs().workflow_memory.smudge_toggle_shortcut.clone();
                    if ui.text_edit_singleline(&mut key).changed() {
                        app.session.prefs.edit(|p| p.workflow_memory.smudge_toggle_shortcut = key);
                    }
                    if !toggle_key.is_empty() && crate::shortcuts::parse(&toggle_key).is_none() {
                        ui.colored_label(egui::Color32::YELLOW, "Invalid shortcut");
                    }
'''
new = '''                    ui.label("Set the toggle key in Edit > Keyboard Shortcuts.");
                    ui.label("Search: Toggle Smudge Strength Preset");
'''
if s.count(old) != 1:
    raise SystemExit("retouch_ui: cannot locate legacy shortcut editor")
s = s.replace(old, new, 1)
(ROOT/p).write_text(s, encoding="utf-8")

# Remove unused legacy preference key; new shortcut lives in prefs.shortcuts.
replace_once(
    "crates/engine/src/prefs.rs",
    '    pub smudge_toggle_shortcut: String,\n',
    ''
)
replace_once(
    "crates/engine/src/prefs.rs",
    '            smudge_toggle_shortcut: String::new(),\n',
    ''
)
print("Applied custom.8: Smudge toggle registered in Keyboard Shortcuts.")
