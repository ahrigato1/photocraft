from pathlib import Path

ROOT = Path('.')


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def write(path, text):
    (ROOT / path).write_text(text, encoding='utf-8')


def replace_once(text, old, new, path):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{path}: expected exactly one match, found {count}: {old[:80]!r}')
    return text.replace(old, new, 1)


# Preferences: remember active workflow/tool state.
p = 'crates/engine/src/prefs.rs'
s = read(p)

s = replace_once(
    s,
    '    pub use_shift_key_for_tool_switch: bool,\n',
    '    pub use_shift_key_for_tool_switch: bool,\n'
    '    /// Custom workflow: plain tool-letter shortcuts select the primary tool instead of cycling/remembering the group.\n'
    '    pub always_primary_tool_shortcuts: bool,\n',
    p,
)
s = replace_once(
    s,
    '            use_shift_key_for_tool_switch: false,\n',
    '            use_shift_key_for_tool_switch: false,\n'
    '            always_primary_tool_shortcuts: false,\n',
    p,
)

marker = '''/// All preferences. JSON keys are the `edit.preferences.<section>` ids.\n'''
insert = '''/// Small pieces of session/tool state that are useful to carry across launches and custom builds.\n/// Kept outside the Preferences sections so they do not clutter Edit > Preferences.\n#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]\n#[serde(default, rename_all = "camelCase")]\npub struct WorkflowMemory {\n    pub brush: photocraft_paint::BrushSettings,\n    /// UI-owned ToolOptions serialized as JSON to avoid an engine -> UI dependency.\n    pub tool_options: Value,\n    /// Most recent folder used by a Save As / export dialog.\n    pub last_save_dir: String,\n}\n\nimpl Default for WorkflowMemory {\n    fn default() -> Self {\n        Self {\n            // Match ToolState's startup brush (not BrushSettings' bare 0%-smoothing default).\n            brush: photocraft_paint::BrushSettings {\n                smoothing: photocraft_paint::brush::Smoothing { amount: 0.1, ..Default::default() },\n                ..Default::default()\n            },\n            tool_options: Value::Null,\n            last_save_dir: String::new(),\n        }\n    }\n}\n\n'''
s = replace_once(s, marker, insert + marker, p)
s = replace_once(
    s,
    '    pub toolbar: ToolbarCustomization,\n',
    '    pub toolbar: ToolbarCustomization,\n'
    '    /// Active brush/tool options and workflow directory remembered across launches.\n'
    '    pub workflow_memory: WorkflowMemory,\n',
    p,
)
write(p, s)

# UI persistence: restore + continuously remember after gestures settle.
p = 'crates/ui-egui/src/prefs_ui.rs'
s = read(p)
s = replace_once(
    s,
    '    crate::dock::restore(app);\n    crate::brush_picker::restore(app);\n    app.sync_recent();\n',
    '    crate::dock::restore(app);\n'
    '    crate::brush_picker::restore(app);\n'
    '    // Custom workflow memory: active brush, per-tool option-bar values, and last output folder.\n'
    '    let memory = app.session.prefs().workflow_memory.clone();\n'
    '    app.session.tools.brush = memory.brush;\n'
    '    if !memory.tool_options.is_null()\n'
    '        && let Ok(options) = serde_json::from_value::<crate::state::ToolOptions>(memory.tool_options)\n'
    '    {\n'
    '        app.ui.tool_options = options;\n'
    '    }\n'
    '    if !memory.last_save_dir.is_empty() {\n'
    '        app.last_save_dir = Some(std::path::PathBuf::from(memory.last_save_dir));\n'
    '    }\n'
    '    app.sync_recent();\n',
    p,
)

anchor = '''/// Per-frame upkeep: theme sync, persistence, autosave and the history log.\npub fn tick(app: &mut PhotocraftApp, ctx: &egui::Context) {\n'''
helper = '''/// Remember the practical editing state that stock PhotoCraft keeps only for this process.\n/// Wait until the pointer is up so a brush/crop slider drag produces one preference revision/write.\nfn persist_workflow_memory(app: &mut PhotocraftApp, ctx: &egui::Context) {\n    if ctx.input(|i| i.pointer.any_down()) {\n        return;\n    }\n    let brush = app.session.tools.brush.clone();\n    let tool_options = serde_json::to_value(&app.ui.tool_options).unwrap_or(Value::Null);\n    let last_save_dir = app.last_save_dir.as_ref().map(|p| p.to_string_lossy().into_owned()).unwrap_or_default();\n    let memory = &app.session.prefs().workflow_memory;\n    if memory.brush != brush || memory.tool_options != tool_options || memory.last_save_dir != last_save_dir {\n        app.session.prefs.edit(|prefs| {\n            prefs.workflow_memory.brush = brush;\n            prefs.workflow_memory.tool_options = tool_options;\n            prefs.workflow_memory.last_save_dir = last_save_dir;\n        });\n    }\n}\n\n'''
s = replace_once(s, anchor, helper + anchor, p)
s = replace_once(
    s,
    '    app.sync_recent();\n    if let Some(wait) = persist(app, ctx.input(|i| i.time)) {\n',
    '    app.sync_recent();\n'
    '    persist_workflow_memory(app, ctx);\n'
    '    if let Some(wait) = persist(app, ctx.input(|i| i.time)) {\n',
    p,
)
write(p, s)

# Tool-letter behavior: make custom direct-primary behavior optional.
p = 'crates/ui-egui/src/shortcuts.rs'
s = read(p)
start_custom = '    // Custom workflow: a tool letter always selects the primary tool shown first in its toolbar\n'
start_stock = '    // Tool keys; pressing the key of the current group cycles within it. With Preferences ›\n'
end_marker = '    // 1–0 set opacity, ⇧1–0 flow or fill (`opacity_keys`).\n'
start = s.find(start_custom)
if start < 0:
    start = s.find(start_stock)
if start < 0:
    raise SystemExit(f'{p}: could not find tool-key block')
end = s.find(end_marker, start)
if end < 0:
    raise SystemExit(f'{p}: could not find end of tool-key block')
new_block = '''    // Custom preference: either deterministic primary tools (B = Brush every time) or stock\n    // PhotoCraft/Photoshop-style group memory/cycling. The sub-tools remain available in flyouts.\n    if app.session.prefs().tools.always_primary_tool_shortcuts {\n        let direct_tools = [\n            (Key::V, Tool::Move),\n            (Key::M, Tool::RectMarquee),\n            (Key::L, Tool::Lasso),\n            (Key::W, Tool::ObjectSelection),\n            (Key::C, Tool::Crop),\n            (Key::I, Tool::Eyedropper),\n            (Key::J, Tool::Remove),\n            (Key::B, Tool::Brush),\n            (Key::S, Tool::CloneStamp),\n            (Key::Y, Tool::HistoryBrush),\n            (Key::E, Tool::Eraser),\n            (Key::G, Tool::Gradient),\n            (Key::O, Tool::Dodge),\n            (Key::P, Tool::Pen),\n            (Key::T, Tool::Type),\n            (Key::A, Tool::PathSelection),\n            (Key::U, Tool::Rectangle),\n            (Key::H, Tool::Hand),\n            (Key::R, Tool::RotateView),\n            (Key::Z, Tool::Zoom),\n        ];\n        for (key, tool) in direct_tools {\n            if pressed(key) {\n                app.ui.tool = tool;\n                return;\n            }\n        }\n    } else {\n        let shift_switch = app.session.prefs().tools.use_shift_key_for_tool_switch;\n        for t in Tool::ALL {\n            let Some(k) = Key::from_name(&t.key().to_string()) else { continue };\n            let cycle_shift = shift_switch && ctx.input_mut(|i| i.consume_key(Modifiers::SHIFT, k));\n            if cycle_shift || pressed(k) {\n                let group: Vec<Tool> = Tool::ALL.iter().copied().filter(|x| x.key() == t.key()).collect();\n                app.ui.tool = match group.iter().position(|x| *x == app.ui.tool) {\n                    Some(i) if shift_switch && !cycle_shift => group[i],\n                    Some(i) => group[(i + 1) % group.len()],\n                    None => app.ui.group_tool(t.key()).unwrap_or(group[0]),\n                };\n                return;\n            }\n        }\n    }\n'''
s = s[:start] + new_block + s[end:]
write(p, s)

# Close All / quit: explicit No to All / Don't Save All.
p = 'crates/ui-egui/src/discard_ui.rs'
s = read(p)

anchor = '''/// Saves `doc`; true once it is saved. A document without a file to write back to asks where in\n'''
helper = '''/// Discard every dirty document still covered by the current batch prompt. Each call to\n/// `advance` closes one answered document; the last one runs Close All / Exit as usual.\nfn discard_all(app: &mut PhotocraftApp, ctx: &egui::Context) {\n    loop {\n        let before = app.discard.as_ref().map_or(0, |p| p.docs.len());\n        if before == 0 {\n            return;\n        }\n        advance(app, ctx);\n        let Some(open) = app.discard.as_ref() else { return };\n        if open.docs.len() >= before {\n            return;\n        }\n    }\n}\n\n'''
s = replace_once(s, anchor, helper + anchor, p)

s = replace_once(
    s,
    '    let (exits, reverts) = (p.id == EXIT, p.id == "file.revert");\n',
    '    let (exits, reverts) = (p.id == EXIT, p.id == "file.revert");\n'
    '    let batch = p.docs.len() > 1 && matches!(reach(&p.id), Some(Reach::All) | Some(Reach::AllButTarget));\n',
    p,
)

old_buttons = '''    let cancel = (ButtonRole::Cancel, "Cancel", mac.then_some(Key::C), 84.0, Answer::Cancel);\n    let buttons = if reverts {\n        vec![(ButtonRole::Default, "Revert", Some(Key::R), 84.0, Answer::Discard), cancel]\n    } else if mac {\n        vec![\n            (ButtonRole::Default, "Save", Some(Key::S), 84.0, Answer::Save),\n            (ButtonRole::Alternate, "Don't Save", Some(Key::D), 100.0, Answer::Discard),\n            cancel,\n        ]\n    } else {\n        vec![(ButtonRole::Default, "Yes", Some(Key::Y), 84.0, Answer::Save), (ButtonRole::Alternate, "No", Some(Key::N), 84.0, Answer::Discard), cancel]\n    };\n'''
new_buttons = '''    let cancel = (ButtonRole::Cancel, "Cancel", mac.then_some(Key::C), 84.0, Answer::Cancel);\n    let buttons = if reverts {\n        vec![(ButtonRole::Default, "Revert", Some(Key::R), 84.0, Answer::Discard), cancel]\n    } else if mac && batch {\n        vec![\n            (ButtonRole::Default, "Save", Some(Key::S), 84.0, Answer::Save),\n            (ButtonRole::Alternate, "Don't Save", Some(Key::D), 100.0, Answer::Discard),\n            (ButtonRole::Cancel, "Don't Save All", Some(Key::A), 120.0, Answer::DiscardAll),\n            (ButtonRole::Apply, "Cancel", Some(Key::C), 84.0, Answer::Cancel),\n        ]\n    } else if mac {\n        vec![\n            (ButtonRole::Default, "Save", Some(Key::S), 84.0, Answer::Save),\n            (ButtonRole::Alternate, "Don't Save", Some(Key::D), 100.0, Answer::Discard),\n            cancel,\n        ]\n    } else if batch {\n        vec![\n            (ButtonRole::Default, "Yes", Some(Key::Y), 84.0, Answer::Save),\n            (ButtonRole::Alternate, "No", Some(Key::N), 84.0, Answer::Discard),\n            (ButtonRole::Cancel, "No to All", Some(Key::A), 96.0, Answer::DiscardAll),\n            (ButtonRole::Apply, "Cancel", Some(Key::C), 84.0, Answer::Cancel),\n        ]\n    } else {\n        vec![(ButtonRole::Default, "Yes", Some(Key::Y), 84.0, Answer::Save), (ButtonRole::Alternate, "No", Some(Key::N), 84.0, Answer::Discard), cancel]\n    };\n'''
s = replace_once(s, old_buttons, new_buttons, p)

s = replace_once(
    s,
    '        Some(Answer::Discard) => advance(app, ctx),\n        Some(Answer::Save) if save(app, ctx, doc) => advance(app, ctx),\n',
    '        Some(Answer::Discard) => advance(app, ctx),\n'
    '        Some(Answer::DiscardAll) => discard_all(app, ctx),\n'
    '        Some(Answer::Save) if save(app, ctx, doc) => advance(app, ctx),\n',
    p,
)
s = replace_once(
    s,
    'enum Answer {\n    Save,\n    Discard,\n    Cancel,\n}',
    'enum Answer {\n    Save,\n    Discard,\n    DiscardAll,\n    Cancel,\n}',
    p,
)
write(p, s)

print('Applied custom.6 workflow persistence and close-all UX changes.')
