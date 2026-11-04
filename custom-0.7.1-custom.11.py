from pathlib import Path

p=Path("crates/ui-egui/src/work_area.rs")
s=p.read_text(encoding="utf-8")

def once(old,new):
    global s
    count=s.count(old)
    if count!=1:
        raise SystemExit(f"Expected one occurrence ({count}): {old[:90]!r}")
    s=s.replace(old,new,1)

once(
'''fn fitted_id() -> egui::Id {
    egui::Id::new("pc-window-fitted")
}
''',
'''fn fitted_id() -> egui::Id {
    egui::Id::new("pc-window-fitted")
}

/// Restore a usable window when Windows reports a tiny root viewport at startup.
/// This is intentionally only a launch-time check: a user can resize later.
fn tiny_window(outer: Vec2, monitor: Vec2) -> bool {
    outer.is_finite()
        && monitor.is_finite()
        && monitor.x > 0.0
        && monitor.y > 0.0
        && (outer.x < 600.0 || outer.y < 360.0)
}

/// egui's requested inner window size is measured in points; monitor and outer
/// rectangles are reported in physical pixels, so account for per-display DPI.
fn recovery_size(monitor_pixels: Vec2, pixels_per_point: f32) -> Vec2 {
    let scale = if pixels_per_point.is_finite() && pixels_per_point > 0.0 {
        pixels_per_point
    } else {
        1.0
    };
    let available = monitor_pixels / scale;
    egui::vec2(
        1100.0_f32.min((available.x - 80.0).max(760.0)),
        760.0_f32.min((available.y - TASKBAR - 50.0).max(480.0)),
    )
}
'''
)
once(
'''    // macOS keeps new windows inside the screen's visible frame itself.
    if cfg!(target_os = "macos") {
        return false;
    }
    ctx.data_mut(|d| d.insert_temp(fitted_id(), true));
    if maximized == Some(true) || fullscreen == Some(true) || !m.is_finite() || !outer.is_finite() || fits(outer.size(), m) {
        return false;
    }
    ctx.send_viewport_cmd(egui::ViewportCommand::Maximized(true));
    true
''',
'''    // macOS keeps new windows inside the screen's visible frame itself.
    if cfg!(target_os = "macos") {
        return false;
    }
    ctx.data_mut(|d| d.insert_temp(fitted_id(), true));
    if maximized == Some(true) || fullscreen == Some(true) || !m.is_finite() || !outer.is_finite() {
        return false;
    }
    // Recover the occasional tiny floating PhotoCraft window after Windows
    // startup / mixed-DPI display changes. Do not override a normal window.
    if tiny_window(outer.size(), m) {
        let size = recovery_size(m, ctx.pixels_per_point());
        ctx.send_viewport_cmd(egui::ViewportCommand::InnerSize(size));
        return true;
    }
    if fits(outer.size(), m) {
        return false;
    }
    ctx.send_viewport_cmd(egui::ViewportCommand::Maximized(true));
    true
'''
)
once(
'''    #[test]
    fn a_window_too_big_for_its_display_is_maximized_once() {
''',
'''    #[test]
    fn tiny_startup_windows_are_recovered_once() {
        assert!(tiny_window(vec2(230.0, 75.0), vec2(2560.0, 1440.0)));
        assert!(!tiny_window(vec2(900.0, 650.0), vec2(2560.0, 1440.0)));
        assert_eq!(recovery_size(vec2(2560.0, 1440.0), 1.0), vec2(1100.0, 760.0));
        assert_eq!(recovery_size(vec2(1920.0, 1080.0), 2.0), vec2(880.0, 442.0_f32.max(480.0)));
        let ctx = egui::Context::default();
        let tiny = Some(Rect::from_min_size(pos2(400.0, 250.0), vec2(230.0, 75.0)));
        assert!(!frame(&ctx, None, tiny, Some(false)).iter().any(|c| matches!(c, egui::ViewportCommand::InnerSize(_))));
        let commands = frame(&ctx, Some(vec2(2560.0, 1440.0)), tiny, Some(false));
        assert!(commands.contains(&egui::ViewportCommand::InnerSize(vec2(1100.0, 760.0))), "{commands:?}");
        assert!(frame(&ctx, Some(vec2(2560.0, 1440.0)), tiny, Some(false)).is_empty());
    }

    #[test]
    fn a_window_too_big_for_its_display_is_maximized_once() {
'''
)
p.write_text(s,encoding="utf-8")
print("Patched launch-only tiny window recovery in work_area::fit_window")
