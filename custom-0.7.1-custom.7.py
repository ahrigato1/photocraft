from pathlib import Path

ROOT = Path(".")

def edit(path, old, new):
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected 1 occurrence, found {count}: {old[:90]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")

# Pixel Grid was enabled in Show::default and not part of the workflow preferences
# remembered by custom.6. Make it off by default and persist user toggles.
edit("crates/ui-egui/src/view_cmds.rs",
     "            pixel_grid: true,\n",
     "            pixel_grid: false,\n")
edit("crates/engine/src/prefs.rs",
     "    pub last_save_dir: String,\n",
     "    pub last_save_dir: String,\n"
     "    /// Remember View > Show > Pixel Grid independently of document/tab changes.\n"
     "    pub pixel_grid: bool,\n"
     "    /// Named Smudge strength slots (percent) and user-defined switching shortcut.\n"
     "    pub smudge_low_strength: f32,\n"
     "    pub smudge_high_strength: f32,\n"
     "    pub smudge_toggle_shortcut: String,\n")
edit("crates/engine/src/prefs.rs",
     "            last_save_dir: String::new(),\n",
     "            last_save_dir: String::new(),\n"
     "            pixel_grid: false,\n"
     "            smudge_low_strength: 18.0,\n"
     "            smudge_high_strength: 70.0,\n"
     "            smudge_toggle_shortcut: String::new(),\n")
edit("crates/ui-egui/src/prefs_ui.rs",
     "    app.session.tools.brush = memory.brush;\n",
     "    app.session.tools.brush = memory.brush;\n"
     "    app.ui.view.show.pixel_grid = memory.pixel_grid;\n")
edit("crates/ui-egui/src/prefs_ui.rs",
     "    let last_save_dir = app.last_save_dir.as_ref().map(|p| p.to_string_lossy().into_owned()).unwrap_or_default();\n",
     "    let last_save_dir = app.last_save_dir.as_ref().map(|p| p.to_string_lossy().into_owned()).unwrap_or_default();\n"
     "    let pixel_grid = app.ui.view.show.pixel_grid;\n")
edit("crates/ui-egui/src/prefs_ui.rs",
     "    if memory.brush != brush || memory.tool_options != tool_options || memory.last_save_dir != last_save_dir {\n",
     "    if memory.brush != brush || memory.tool_options != tool_options || memory.last_save_dir != last_save_dir || memory.pixel_grid != pixel_grid {\n")
edit("crates/ui-egui/src/prefs_ui.rs",
     "            prefs.workflow_memory.last_save_dir = last_save_dir;\n",
     "            prefs.workflow_memory.last_save_dir = last_save_dir;\n"
     "            prefs.workflow_memory.pixel_grid = pixel_grid;\n")

# Keep multiple selected editable text/shape/group layers, including layer effects,
# rather than reducing them to the active layer. Pixels remain available for external paste.
p="crates/engine/src/edit_cmds.rs"
s=(ROOT/p).read_text(encoding="utf-8")
anchor="fn has_doc(s: &Session) -> std::result::Result<(), String> {\n"
assert s.count(anchor)==1
helper='''/// Whole selected layers for same-app paste; keeps text, effects, group hierarchy
/// and stacking. Only used when there is no pixel selection to constrain Copy.
fn whole_selected_layers(d: &crate::DocState) -> Option<Box<Document>> {
    if d.doc.selection.is_some() || d.selected_layers().len() <= 1 || !crate::layer_copy_cmds::layered(d.doc.mode) {
        return None;
    }
    let ids = crate::layer_multi_cmds::top_level(&d.doc, &d.selected_layers());
    if ids.is_empty() {
        return None;
    }
    let src = &d.doc;
    let mut copies = Document::new("", src.size, src.mode, src.depth);
    copies.icc_profile = src.icc_profile.clone();
    copies.resolution_dpi = src.resolution_dpi;
    copies.patterns = src.patterns.clone();
    for id in ids {
        copies.layers.push(src.layer(id)?.clone());
    }
    Some(Box::new(copies))
}

'''
s=s.replace(anchor,helper+anchor,1)
old='''    has_layer_pixels(s).or_else(|e| s.active().and_then(|d| d.active_layer.filter(|id| takes_whole(d, *id))).map(|_| ()).ok_or(e))
'''
new='''    has_layer_pixels(s).or_else(|e| {
        s.active().and_then(|d| {
            if whole_selected_layers(d).is_some() {
                Some(())
            } else {
                d.active_layer.filter(|id| takes_whole(d, *id)).map(|_| ())
            }
        }).ok_or(e)
    })
'''
assert s.count(old)==1
s=s.replace(old,new,1)
old='''    } else {
        let id = d.active_layer.ok_or(EngineError::Other("no active layer".into()))?;
        let layers = whole_layer(d, id);
'''
new='''    } else if let Some(copies) = whole_selected_layers(d) {
        // Create both a native multi-layer clipboard and a flattened pixel preview;
        // ordinary Paste restores each editable layer and all its effects.
        let mut shown = (*copies).clone();
        for l in &mut shown.layers {
            l.visible = true;
        }
        Clip { layers: Some(copies), ..lift(&merged_surface(&shown), None, canvas)? }
    } else {
        let id = d.active_layer.ok_or(EngineError::Other("no active layer".into()))?;
        let layers = whole_layer(d, id);
'''
assert s.count(old)==1
s=s.replace(old,new,1)
(ROOT/p).write_text(s,encoding="utf-8")

# Smudge presets live beside Strength in the Smudge options bar. Two slots can be
# edited in-place and are saved by the normal preferences autowrite mechanism.
p="crates/ui-egui/src/retouch_ui.rs"
s=(ROOT/p).read_text(encoding="utf-8")
old='''            if tool == Tool::Smudge {
                crate::widgets::checkbox(ui, &mut o.finger_painting, tl!("Finger Painting"));
            }
'''
new='''            if tool == Tool::Smudge {
                crate::widgets::checkbox(ui, &mut o.finger_painting, tl!("Finger Painting"));
                let memory = &app.session.prefs().workflow_memory;
                let low = memory.smudge_low_strength.clamp(1.0, 100.0);
                let high = memory.smudge_high_strength.clamp(1.0, 100.0);
                let toggle_key = memory.smudge_toggle_shortcut.clone();
                if !toggle_key.is_empty()
                    && !ui.ctx().wants_keyboard_input()
                    && let Some(shortcut) = crate::shortcuts::parse(&toggle_key)
                    && crate::shortcuts::consume(ui.ctx(), &shortcut)
                {
                    // Whichever slot is currently closer is the one we leave.
                    o.strength = if (o.strength - low).abs() <= (o.strength - high).abs() { high } else { low };
                }
                egui::ComboBox::from_id_salt("smudge-strength-presets")
                    .selected_text("Presets")
                    .width(90.0)
                    .show_ui(ui, |ui| {
                        ui.selectable_value(&mut o.strength, low, format!("Soft  {:.0}%", low));
                        ui.selectable_value(&mut o.strength, high, format!("Strong  {:.0}%", high));
                    });
                ui.menu_button("⚙", |ui| {
                    ui.label("Smudge strength presets");
                    let mut low = app.session.prefs().workflow_memory.smudge_low_strength;
                    if ui.horizontal(|ui| {
                        ui.label("Soft");
                        ui.add(egui::DragValue::new(&mut low).range(1.0..=100.0).suffix(" %"))
                    }).inner.changed() {
                        app.session.prefs.edit(|p| p.workflow_memory.smudge_low_strength = low.clamp(1.0, 100.0));
                    }
                    let mut high = app.session.prefs().workflow_memory.smudge_high_strength;
                    if ui.horizontal(|ui| {
                        ui.label("Strong");
                        ui.add(egui::DragValue::new(&mut high).range(1.0..=100.0).suffix(" %"))
                    }).inner.changed() {
                        app.session.prefs.edit(|p| p.workflow_memory.smudge_high_strength = high.clamp(1.0, 100.0));
                    }
                    ui.label("Toggle shortcut (e.g. F6 or Ctrl+Alt+M):");
                    let mut key = app.session.prefs().workflow_memory.smudge_toggle_shortcut.clone();
                    if ui.text_edit_singleline(&mut key).changed() {
                        app.session.prefs.edit(|p| p.workflow_memory.smudge_toggle_shortcut = key);
                    }
                    if !toggle_key.is_empty() && crate::shortcuts::parse(&toggle_key).is_none() {
                        ui.colored_label(egui::Color32::YELLOW, "Invalid shortcut");
                    }
                });
            }
'''
assert s.count(old)==1
s=s.replace(old,new,1)
(ROOT/p).write_text(s,encoding="utf-8")
print("Applied custom.7: pixel grid persistence, editable multi-layer Copy, Smudge strength slots.")
