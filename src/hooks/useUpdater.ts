import { useState, useEffect, useCallback, useRef } from "react";
import {
  checkForUpdate,
  downloadAndInstallUpdate,
  onUpdateProgress,
  UpdateInfo,
  UpdateProgress,
} from "../services/updaterService";

interface UpdaterState {
  updateAvailable: boolean;
  updateInfo: UpdateInfo | null;
  checking: boolean;
  downloading: boolean;
  progress: UpdateProgress | null;
  error: string | null;
  dismissed: boolean;
}

export function useUpdater(checkOnMount = true) {
  const [state, setState] = useState<UpdaterState>({
    updateAvailable: false,
    updateInfo: null,
    checking: false,
    downloading: false,
    progress: null,
    error: null,
    dismissed: false,
  });

  const unlistenRef = useRef<(() => void) | null>(null);

  const check = useCallback(async () => {
    setState((prev) => ({ ...prev, checking: true, error: null }));
    try {
      const info = await checkForUpdate();
      if (info) {
        setState((prev) => ({
          ...prev,
          updateAvailable: true,
          updateInfo: info,
          checking: false,
        }));
      } else {
        setState((prev) => ({
          ...prev,
          updateAvailable: false,
          updateInfo: null,
          checking: false,
        }));
      }
    } catch (err) {
      setState((prev) => ({
        ...prev,
        checking: false,
        error: err instanceof Error ? err.message : String(err),
      }));
    }
  }, []);

  const dismiss = useCallback(() => {
    setState((prev) => ({ ...prev, dismissed: true }));
  }, []);

  const install = useCallback(async () => {
    setState((prev) => ({ ...prev, downloading: true, error: null }));
    try {
      await downloadAndInstallUpdate();
    } catch (err) {
      setState((prev) => ({
        ...prev,
        downloading: false,
        error: err instanceof Error ? err.message : String(err),
      }));
    }
  }, []);

  useEffect(() => {
    let unlisten: (() => void) | null = null;

    onUpdateProgress((p) => {
      setState((prev) => ({ ...prev, progress: p }));
    }).then((fn) => {
      unlisten = fn;
      unlistenRef.current = fn;
    });

    return () => {
      if (unlisten) unlisten();
    };
  }, []);

  useEffect(() => {
    if (checkOnMount) {
      check();
    }
  }, [checkOnMount, check]);

  return {
    ...state,
    check,
    dismiss,
    install,
  };
}
