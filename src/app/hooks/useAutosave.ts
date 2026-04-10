import { useEffect, useRef } from "react";

const DEBOUNCE_MS = 800;
const STORAGE_PREFIX = "pm_sidekick_draft_";

export function useAutosave<T>(key: string, value: T) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);

    timerRef.current = setTimeout(() => {
      try {
        localStorage.setItem(
          `${STORAGE_PREFIX}${key}`,
          JSON.stringify({ value, savedAt: Date.now() }),
        );
      } catch {
        // localStorage quota exceeded — silent
      }
    }, DEBOUNCE_MS);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [key, value]);
}

export function loadDraft<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(`${STORAGE_PREFIX}${key}`);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { value: T; savedAt: number };
    // Expire drafts after 7 days
    const age = Date.now() - parsed.savedAt;
    if (age > 7 * 24 * 60 * 60 * 1000) {
      localStorage.removeItem(`${STORAGE_PREFIX}${key}`);
      return null;
    }
    return parsed.value;
  } catch {
    return null;
  }
}

export function clearDraft(key: string) {
  localStorage.removeItem(`${STORAGE_PREFIX}${key}`);
}
