import type { Lang } from "./i18n";

const KEY = "waymark.lang";

export const parseLang = (v: unknown): Lang | null => (v === "en" || v === "hi" ? v : null);

/** Signed-in users use their saved language; public pages use the local choice, then English. */
export const resolveLang = (userLang: string | undefined, local: Lang | null): Lang => parseLang(userLang) ?? local ?? "en";

export function readLocalLang(): Lang | null {
  try {
    return parseLang(localStorage.getItem(KEY));
  } catch {
    return null;
  }
}

export function writeLocalLang(l: Lang): void {
  try {
    localStorage.setItem(KEY, l);
  } catch {
    /* storage blocked: the choice lasts until reload */
  }
  listeners.forEach((f) => f());
}

const listeners = new Set<() => void>();
export function subscribeLang(f: () => void): () => void {
  listeners.add(f);
  window.addEventListener("storage", f);
  return () => {
    listeners.delete(f);
    window.removeEventListener("storage", f);
  };
}
