import type { RuleVersion } from "./types";

export const EDITABLE = ["enabled", "params", "hard_stop", "message_en", "message_hi"] as const;
type Editable = (typeof EDITABLE)[number];

export function parseParams(text: string): { ok: true; value: Record<string, unknown> } | { ok: false; error: string } {
  try {
    const v: unknown = JSON.parse(text);
    if (v === null || typeof v !== "object" || Array.isArray(v)) return { ok: false, error: "rules.err.object" };
    return { ok: true, value: v as Record<string, unknown> };
  } catch {
    return { ok: false, error: "rules.err.json" };
  }
}

export function diffVersions(a: Pick<RuleVersion, Editable>, b: Pick<RuleVersion, Editable>) {
  return EDITABLE.filter((f) => JSON.stringify(a[f]) !== JSON.stringify(b[f])).map((f) => ({
    field: f, from: a[f], to: b[f],
  }));
}
