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

export type RuleHealthRow = {
  code: string; raised: number; open: number; under_review: number; resolved: number; dismissed: number;
  dismissed_share: number | null; median_days_to_close: number | null; oldest_open_days: number | null;
};

export const dash = (n: number | null) => (n === null ? "-" : String(n));
export const healthShare = (s: number | null) => (s === null ? "-" : `${Math.round(s * 100)}%`);
export const oftenDismissed = (r: Pick<RuleHealthRow, "resolved" | "dismissed" | "dismissed_share">) =>
  r.dismissed_share !== null && r.dismissed_share >= 0.5 && r.resolved + r.dismissed >= 5;
