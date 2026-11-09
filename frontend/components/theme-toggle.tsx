"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";
import { useAuth } from "@/lib/auth";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const { t } = useAuth();
  // resolvedTheme is only known on the client; render the neutral label until hydrated.
  const mounted = useSyncExternalStore(() => () => {}, () => true, () => false);
  const dark = mounted && resolvedTheme === "dark";
  return (
    <button
      type="button"
      onClick={() => setTheme(dark ? "light" : "dark")}
      aria-label={t(dark ? "theme.toLight" : "theme.toDark")}
      className="inline-flex h-11 items-center md:h-9 gap-2 rounded-md border border-border px-3 text-sm hover:bg-accent"
    >
      {dark ? <Sun size={16} aria-hidden /> : <Moon size={16} aria-hidden />}
      {t(dark ? "theme.light" : "theme.dark")}
    </button>
  );
}
