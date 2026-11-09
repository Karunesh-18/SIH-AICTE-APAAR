import type { Role } from "./nav";

export type FlagAction = "review" | "resolve" | "dismiss" | "ask" | "link" | "reply";
export const FLAG_STATES = ["open", "under_review", "ask_institution", "resolved", "dismissed"] as const;
export const RULE_CODES = ["R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08"] as const;

// Mirrors backend/app/domain/flags.py: state -> actions the state machine accepts.
const FROM: Record<string, FlagAction[]> = {
  open: ["review", "resolve", "dismiss", "ask"],
  under_review: ["resolve", "dismiss", "ask"],
  ask_institution: ["review", "resolve", "dismiss"],
};
const AICTE = new Set<Role>(["AICTE_ADMIN", "AICTE_OFFICER"]);
const INSTITUTION = new Set<Role>(["INSTITUTION_ADMIN", "INSTITUTION_STAFF"]);

/** UI convenience only: the server still enforces role, scope and state (409/403). */
export function allowedActions(state: string, role: Role | undefined, rule: string): FlagAction[] {
  if (role && INSTITUTION.has(role)) return state === "ask_institution" ? ["reply"] : [];
  if (!role || !AICTE.has(role)) return [];
  const a = FROM[state] ?? [];
  return rule === "R08" && a.length ? [...a, "link"] : a;
}

export const noteError = (note: string): string | null => (note.trim() ? null : "flag.note.required");

export function formatAge(days: number): { key: string; n: number } {
  return { key: days === 0 ? "age.today" : days === 1 ? "age.day" : "age.days", n: days };
}

const FILTERS = ["state", "rule", "institution", "region", "age_days"] as const;
export type Filters = Record<(typeof FILTERS)[number], string> & { offset: number };

export function filtersFromQuery(p: URLSearchParams): Filters {
  const off = Number(p.get("offset"));
  return {
    ...(Object.fromEntries(FILTERS.map((k) => [k, p.get(k) ?? ""])) as Record<(typeof FILTERS)[number], string>),
    offset: Number.isInteger(off) && off > 0 ? off : 0,
  };
}

export function filtersToQuery(f: Filters): string {
  const q = new URLSearchParams();
  for (const k of FILTERS) if (f[k]) q.set(k, f[k]);
  if (f.offset > 0) q.set("offset", String(f.offset));
  return q.toString();
}

const ORDER: Record<string, string[]> = {
  R02: ["found", "expected_digits", "digits_found", "checksum"],
  R03: ["submitted", "registry", "similarity", "threshold"],
  R04: ["apaar_id", "count"],
  R05: ["apaar_id"],
  R06: ["approved_intake", "supernumerary_seats", "allowed", "actual", "excess"],
};

/** Evidence as labelled numbers (label key = `ev.<key>`), never raw JSON. */
export function evidenceFacts(rule: string, ev: Record<string, unknown>): { facts: { key: string; value: string }[]; orderingOnly: boolean } {
  const e = ev ?? {};
  const scalar = (k: string) => k in e && e[k] !== null && typeof e[k] !== "object";
  const keys = ORDER[rule]?.filter(scalar) ?? Object.keys(e).filter((k) => k !== "ordering_only" && scalar(k));
  return { facts: keys.map((key) => ({ key, value: String(e[key]) })), orderingOnly: e.ordering_only === true };
}

export type Side = { institution?: string; programme: string; admission_date: string | null };
export function r05Sides(ev: Record<string, unknown>): { here: Side | null; elsewhere: Side[] } {
  return { here: (ev?.this as Side) ?? null, elsewhere: Array.isArray(ev?.elsewhere) ? (ev.elsewhere as Side[]) : [] };
}
