"use client";
import { useAuth } from "@/lib/auth";
import type { ClearHintData } from "@/lib/types";

const fill = (s: string, v: Record<string, unknown>) => s.replace(/\{(\w+)\}/g, (m, k) => (k in v ? String(v[k]) : m));

/** Muted "To clear:" line under a flag's reason. Renders nothing when there is no hint. */
export function ClearHint({ hint }: { hint?: ClearHintData | null }) {
  const { t } = useAuth();
  if (!hint) return null;
  let text = fill(t(hint.key), hint.values);
  if (/\{\w+\}/.test(text)) text = fill(t(`${hint.key}.short`), hint.values); // evidence lacked a number
  if (text === `${hint.key}.short` || /\{\w+\}/.test(text)) return null;
  return <p className="text-sm text-muted-foreground">{t("hint.prefix")} {text}</p>;
}
