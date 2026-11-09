// Pure helpers for dashboards, charts, reports, windows and the demo clock.

export type InstRow = { id: string; name: string; enrolled: number; allowed: number };
export type IntakeBar = InstRow & { within: number; headroom: number; over: number; excess: boolean };

/** Split each bar so the cap is where headroom ends and the excess begins; excess rows first. */
export function intakeBars(rows: InstRow[]): IntakeBar[] {
  return rows
    .map((r) => ({
      ...r,
      within: Math.min(r.enrolled, r.allowed),
      headroom: Math.max(r.allowed - r.enrolled, 0),
      over: Math.max(r.enrolled - r.allowed, 0),
      excess: r.enrolled > r.allowed,
    }))
    .sort((a, b) => b.over - a.over || b.enrolled / (b.allowed || 1) - a.enrolled / (a.allowed || 1));
}

// R01-R08 own a fixed colour slot each; the scheduled rules R09+ fold into one neutral "other".
const SLOTS = ["R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08"];
export const ruleColor = (k: string): string => {
  const i = SLOTS.indexOf(k);
  return i < 0 ? "var(--chart-other)" : `var(--chart-${i + 1})`;
};

export function ruleStack(rows: { month: string; rule: string; count: number }[]) {
  const months = new Map<string, Record<string, number | string>>();
  const used = new Set<string>();
  for (const r of rows) {
    const k = SLOTS.includes(r.rule) ? r.rule : "other";
    used.add(k);
    const m = months.get(r.month) ?? { month: r.month };
    m[k] = ((m[k] as number) ?? 0) + r.count;
    months.set(r.month, m);
  }
  const keys = [...SLOTS, "other"].filter((k) => used.has(k));
  const data = [...months.values()].sort((a, b) => String(a.month).localeCompare(String(b.month)));
  return { data, keys };
}

export const fmtInt = (n: number): string => n.toLocaleString("en-US");
export const fmtPct = (n: number): string => `${n.toFixed(1)}%`;

export function countdown(closesAt: string, now: Date = new Date()) {
  const ms = new Date(closesAt).getTime() - now.getTime();
  const abs = Math.abs(ms) / 36e5;
  return { state: ms >= 0 ? ("open" as const) : ("closed" as const), days: Math.floor(abs / 24), hours: Math.floor(abs % 24) };
}

export const csvFilename = (key: string): string => `${key}.csv`;

export function reportQuery(filters: Record<string, string>, format: "json" | "csv"): string {
  const p = new URLSearchParams({ format });
  for (const [k, v] of Object.entries(filters)) if (v) p.set(k, v);
  return p.toString();
}

/** Authenticated download: the blob comes from the API client, the anchor click saves it. */
export function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export const clockLabel = (days: number): string | null => (days === 0 ? null : `${days > 0 ? "+" : ""}${days}`);

export type LadderStep = { step: string; offset_hours: number; audience: "institution" | "officer" | "admin" };
export const ladderValid = (l: LadderStep[]): boolean =>
  l.every((s) => s.step.trim()) && new Set(l.map((s) => s.step.trim())).size === l.length;

// Window times are edited in UTC to keep the form unambiguous.
export const toLocalInput = (iso: string): string => new Date(iso).toISOString().slice(0, 16);
export const fromLocalInput = (v: string): string => new Date(`${v}:00Z`).toISOString();
