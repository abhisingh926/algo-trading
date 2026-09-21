"use client";

import { useCallback, useSyncExternalStore } from "react";

const listeners = new Set<() => void>();
/** In-memory fallback for when localStorage is unavailable. */
const memory = new Set<string>();
const notify = () => listeners.forEach((l) => l());

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

function read(key: string): boolean {
  try {
    return window.localStorage.getItem(key) === "1";
  } catch {
    return false;
  }
}

/** A persisted boolean in localStorage. Storage access can fail (private mode, blocked): then it is in-memory only. */
export function useLocalFlag(key: string): [boolean, (value: boolean) => void] {
  // Hydrate as `true` so a dismissed banner never flashes; the client snapshot takes over immediately.
  const value = useSyncExternalStore(subscribe, () => read(key) || memory.has(key), () => true);
  const set = useCallback(
    (next: boolean) => {
      if (next) memory.add(key);
      else memory.delete(key);
      try {
        if (next) window.localStorage.setItem(key, "1");
        else window.localStorage.removeItem(key);
      } catch {
        /* storage unavailable: memory fallback above keeps the session consistent */
      }
      notify();
    },
    [key],
  );
  return [value, set];
}
