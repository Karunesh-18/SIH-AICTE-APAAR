"use client";
import { Languages } from "lucide-react";
import { useAuth } from "@/lib/auth";

/** en/hi toggle. Signed-in: saved to the account (PATCH /auth/me). Public: kept in localStorage. */
export function LangSwitch() {
  const { lang, setLang, t } = useAuth();
  const next = lang === "en" ? "hi" : "en";
  return (
    <button type="button" onClick={() => setLang(next)} lang={next}
            aria-label={t("lang.switch")}
            className="inline-flex h-11 items-center gap-2 rounded-md border border-border px-3 text-sm hover:bg-accent md:h-9">
      <Languages size={16} aria-hidden />
      {next === "hi" ? "हिन्दी" : "English"}
    </button>
  );
}
