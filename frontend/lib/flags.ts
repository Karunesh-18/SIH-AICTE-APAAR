import type { FlagItem } from "./types";

const fmt = (v: unknown): string =>
  Array.isArray(v) ? v.map(fmt).join("; ")
  : v && typeof v === "object" ? Object.values(v as object).map(fmt).join(", ")
  : String(v);

export function evidenceLines(ev: Record<string, unknown>): { key: string; value: string }[] {
  return Object.entries(ev ?? {})
    .filter(([k]) => k !== "ordering_only")
    .map(([key, v]) => ({ key, value: fmt(v) }));
}

export function explainFlag(f: FlagItem) {
  return {
    code: f.rule_code,
    reason: f.reason,
    rows: f.rows.join(", "),
    lines: evidenceLines(f.evidence),
    note: f.evidence?.ordering_only ? "flag.r06.ordering" : null,
  };
}
