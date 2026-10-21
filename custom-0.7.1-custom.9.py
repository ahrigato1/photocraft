from pathlib import Path

def replace_once(path, old, new):
    p = Path(path)
    s = p.read_text(encoding="utf-8")
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"{path}: expected exactly one match (found {n}) for {old[:90]!r}")
    p.write_text(s.replace(old, new, 1), encoding="utf-8")

# custom.8 registered this shortcut and its handler but forgot the shell command
# availability check. Shortcut dispatch rejects any command that is not enabled.
replace_once(
    "crates/ui-egui/src/menus.rs",
    '''pub fn is_enabled(app: &PhotocraftApp, id: &str) -> bool {
    if id == "ui.symmetryTransform" {
''',
    '''pub fn is_enabled(app: &PhotocraftApp, id: &str) -> bool {
    if id == "ui.smudgeToggleStrength" {
        return app.active_tool() == crate::state::Tool::Smudge && app.session.active().is_some();
    }
    if id == "ui.symmetryTransform" {
'''
)
# Check the currently active tool consistently in the command and the enable gate.
replace_once(
    "crates/ui-egui/src/menus.rs",
    '''    if id == "ui.smudgeToggleStrength" {
        if app.ui.tool != crate::state::Tool::Smudge {
''',
    '''    if id == "ui.smudgeToggleStrength" {
        if app.active_tool() != crate::state::Tool::Smudge {
'''
)
# Reflect the current strength without forcing it into one of the preset slots.
replace_once(
    "crates/ui-egui/src/retouch_ui.rs",
    '''                egui::ComboBox::from_id_salt("smudge-strength-presets")
                    .selected_text("Presets")
''',
    '''                let active_label = if (o.strength - low).abs() < 0.05 {
                    format!("Soft  {:.0}%", low)
                } else if (o.strength - high).abs() < 0.05 {
                    format!("Strong  {:.0}%", high)
                } else {
                    format!("Custom  {:.0}%", o.strength)
                };
                egui::ComboBox::from_id_salt("smudge-strength-presets")
                    .selected_text(active_label)
'''
)
print("custom.9: fixed toggle command availability and live preset label.")
