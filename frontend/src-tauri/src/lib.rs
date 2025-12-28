use keyring::Entry;
use serde::{Deserialize, Serialize};

const SERVICE_NAME: &str = "alabama-auction-watcher";

#[derive(Debug, Serialize, Deserialize)]
pub struct ServerInfo {
    server_url: String,
    is_development: bool,
    tauri_version: String,
}

// Store authentication token securely using system keyring
#[tauri::command]
fn store_auth_token(token: String, refresh_token: Option<String>) -> Result<bool, String> {
    let entry = Entry::new(SERVICE_NAME, "auth_token").map_err(|e| e.to_string())?;
    entry.set_password(&token).map_err(|e| e.to_string())?;

    if let Some(refresh) = refresh_token {
        let refresh_entry = Entry::new(SERVICE_NAME, "refresh_token").map_err(|e| e.to_string())?;
        refresh_entry.set_password(&refresh).map_err(|e| e.to_string())?;
    }

    Ok(true)
}

// Retrieve authentication token from system keyring
#[tauri::command]
fn get_auth_token() -> Result<Option<String>, String> {
    let entry = Entry::new(SERVICE_NAME, "auth_token").map_err(|e| e.to_string())?;
    match entry.get_password() {
        Ok(password) => Ok(Some(password)),
        Err(keyring::Error::NoEntry) => Ok(None),
        Err(e) => Err(e.to_string()),
    }
}

// Clear stored authentication tokens
#[tauri::command]
fn clear_auth_tokens() -> Result<bool, String> {
    if let Ok(entry) = Entry::new(SERVICE_NAME, "auth_token") {
        let _ = entry.delete_credential();
    }
    if let Ok(entry) = Entry::new(SERVICE_NAME, "refresh_token") {
        let _ = entry.delete_credential();
    }
    Ok(true)
}

// Get server configuration info
#[tauri::command]
fn get_server_info() -> ServerInfo {
    ServerInfo {
        server_url: "http://localhost:8001".to_string(),
        is_development: cfg!(debug_assertions),
        tauri_version: env!("CARGO_PKG_VERSION").to_string(),
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_os::init())
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            store_auth_token,
            get_auth_token,
            clear_auth_tokens,
            get_server_info,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
