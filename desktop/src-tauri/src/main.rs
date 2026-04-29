// Tauri shell that spawns the bundled Python sidecar on startup
// and kills it on window close.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;
use serde::Serialize;
use tauri::api::process::{Command, CommandChild, CommandEvent};
use tauri::{Manager, WindowBuilder, WindowUrl, PhysicalPosition, PhysicalSize};

struct Sidecar(Mutex<Option<CommandChild>>);

// -------- Monitor / scoreboard window commands --------
#[derive(Serialize)]
struct MonitorInfo {
    index: usize,
    name: String,
    x: i32,
    y: i32,
    width: u32,
    height: u32,
    scale_factor: f64,
    is_primary: bool,
}

#[tauri::command]
fn list_monitors(app: tauri::AppHandle) -> Result<Vec<MonitorInfo>, String> {
    let main = app.get_window("main").ok_or("main window missing")?;
    let monitors = main.available_monitors().map_err(|e| e.to_string())?;
    let primary_pos = main.primary_monitor().ok().flatten().map(|m| *m.position());
    Ok(monitors.into_iter().enumerate().map(|(i, m)| {
        let name = m.name().cloned().unwrap_or_else(|| format!("Display {}", i + 1));
        let pos = m.position();
        let sz = m.size();
        let is_primary = primary_pos.map_or(false, |p| p == *pos);
        MonitorInfo {
            index: i,
            name,
            x: pos.x,
            y: pos.y,
            width: sz.width,
            height: sz.height,
            scale_factor: m.scale_factor(),
            is_primary,
        }
    }).collect())
}

#[tauri::command]
async fn open_scoreboard_window(
    app: tauri::AppHandle,
    monitor_index: usize,
    fullscreen: bool,
) -> Result<(), String> {
    let label = format!("scoreboard-{}", monitor_index);

    // Close existing window with this label so a re-open lands cleanly
    if let Some(existing) = app.get_window(&label) {
        let _ = existing.close();
    }

    // Resolve the chosen monitor
    let main = app.get_window("main").ok_or("main window missing")?;
    let monitors = main.available_monitors().map_err(|e| e.to_string())?;
    let mon = monitors.get(monitor_index).ok_or_else(|| {
        format!("monitor index {} out of range ({} available)", monitor_index, monitors.len())
    })?;
    let pos = *mon.position();
    let size = *mon.size();

    // Build hidden so we can position before showing - prevents a flash
    // on the wrong monitor before fullscreen kicks in.
    let win = WindowBuilder::new(
        &app,
        label,
        WindowUrl::App("index.html".into()),
    )
    .title("Scoreboard")
    .resizable(true)
    .visible(false)
    .initialization_script("window.__NHLSB_SCOREBOARD__ = true;")
    .build()
    .map_err(|e| e.to_string())?;

    win.set_position(PhysicalPosition::new(pos.x, pos.y))
        .map_err(|e| e.to_string())?;
    win.set_size(PhysicalSize::new(size.width, size.height))
        .map_err(|e| e.to_string())?;
    win.show().map_err(|e| e.to_string())?;

    if fullscreen {
        win.set_fullscreen(true).map_err(|e| e.to_string())?;
    }

    Ok(())
}

fn main() {
    tauri::Builder::default()
        .manage(Sidecar(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![list_monitors, open_scoreboard_window])
        .setup(|app| {
            // Spawn the bundled "nhlsb-server" sidecar
            let (mut rx, child) = Command::new_sidecar("nhlsb-server")
                .expect("failed to find nhlsb-server sidecar")
                .args(["--host", "127.0.0.1", "--port", "8765"])
                .spawn()
                .expect("failed to spawn sidecar");

            app.state::<Sidecar>().0.lock().unwrap().replace(child);

            // Drain stdout/stderr so the pipe doesn't fill up
            tauri::async_runtime::spawn(async move {
                while let Some(event) = rx.recv().await {
                    if let CommandEvent::Stderr(line) = event {
                        eprintln!("[sidecar] {}", line);
                    }
                }
            });

            Ok(())
        })
        .on_window_event(|event| {
            // Only kill the sidecar when the MAIN window is destroyed;
            // closing a scoreboard window must not take down the backend.
            if let tauri::WindowEvent::Destroyed = event.event() {
                if event.window().label() != "main" {
                    return;
                }
                let app = event.window().app_handle();
                if let Some(state) = app.try_state::<Sidecar>() {
                    if let Some(child) = state.0.lock().unwrap().take() {
                        let _ = child.kill();
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
