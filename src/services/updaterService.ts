import { invoke } from "@tauri-apps/api/core";
import { listen, UnlistenFn } from "@tauri-apps/api/event";

export interface UpdateInfo {
  version: string;
  notes: string;
  date: string | null;
}

export interface UpdateProgress {
  event: string;
  chunk_length: number | null;
  content_length: number | null;
}

export async function checkForUpdate(): Promise<UpdateInfo | null> {
  return invoke<UpdateInfo | null>("check_for_update");
}

export async function downloadAndInstallUpdate(): Promise<void> {
  return invoke<void>("download_and_install_update");
}

export function onUpdateProgress(
  callback: (progress: UpdateProgress) => void,
): Promise<UnlistenFn> {
  return listen<UpdateProgress>("updater:progress", (event) => {
    callback(event.payload);
  });
}
