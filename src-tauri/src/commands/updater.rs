use serde::Serialize;
use tauri::{AppHandle, Emitter, Manager};

#[derive(Serialize, Clone)]
pub struct UpdateInfo {
    pub version: String,
    pub notes: String,
    pub date: Option<String>,
}

#[derive(Serialize, Clone)]
pub struct UpdateProgress {
    pub event: String,
    pub chunk_length: Option<u64>,
    pub content_length: Option<u64>,
}

#[tauri::command]
pub async fn check_for_update(app: AppHandle) -> Result<Option<UpdateInfo>, String> {
    let updater = app
        .updater()
        .map_err(|e| format!("Failed to get updater: {}", e))?;

    match updater.check().await {
        Ok(Some(update)) => Ok(Some(UpdateInfo {
            version: update.version.clone(),
            notes: update.body.clone().unwrap_or_default(),
            date: update.date.as_ref().map(|d| d.to_string()),
        })),
        Ok(None) => Ok(None),
        Err(e) => Err(format!("Update check failed: {}", e)),
    }
}

#[tauri::command]
pub async fn download_and_install_update(app: AppHandle) -> Result<(), String> {
    let updater = app
        .updater()
        .map_err(|e| format!("Failed to get updater: {}", e))?;

    let update = updater
        .check()
        .await
        .map_err(|e| format!("Update check failed: {}", e))?
        .ok_or("No update available")?;

    let app_clone = app.clone();
    let app_clone2 = app.clone();
    update
        .download_and_install(
            move |chunk_length, content_length| {
                let _ = app_clone.emit(
                    "updater:progress",
                    UpdateProgress {
                        event: "Progress".to_string(),
                        chunk_length: Some(chunk_length as u64),
                        content_length,
                    },
                );
            },
            move || {
                let _ = app_clone2.emit(
                    "updater:progress",
                    UpdateProgress {
                        event: "Finished".to_string(),
                        chunk_length: None,
                        content_length: None,
                    },
                );
            },
        )
        .await
        .map_err(|e| format!("Download/install failed: {}", e))?;

    app.restart();
}
