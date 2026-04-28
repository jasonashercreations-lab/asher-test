// Tauri shell that spawns the bundled Python sidecar on startup
// and kills it on window close.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;
use tauri::api::process::{Command, CommandChild, CommandEvent};
use tauri::Manager;

struct Sidecar(Mutex<Option<CommandChild>>);

fn main() {
    tauri::Builder::default()
        .manage(Sidecar(Mutex::new(None)))
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
            if let tauri::WindowEvent::Destroyed = event.event() {
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
