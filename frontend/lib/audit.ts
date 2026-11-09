import type { AuditRow } from "./types";

export type AuditFilters = { role?: string; action?: string; entity?: string; from?: string; to?: string };

/** Client-side filter over the rows already loaded (the API pages by limit/offset only). Dates are inclusive, UTC. */
export function filterAudit(rows: AuditRow[], f: AuditFilters): AuditRow[] {
  const from = f.from ? Date.parse(`${f.from}T00:00:00Z`) : null;
  const to = f.to ? Date.parse(`${f.to}T23:59:59.999Z`) : null;
  const action = f.action?.trim().toLowerCase();
  return rows.filter((r) => {
    const at = Date.parse(r.occurred_at);
    return (!f.role || r.actor_role === f.role)
      && (!action || r.action.toLowerCase().includes(action))
      && (!f.entity || r.entity_type === f.entity)
      && (from === null || at >= from)
      && (to === null || at <= to);
  });
}

export type PolicyVersion = { id: number; version: number; allowed_fields: string[]; note: string | null; at: string; actor_role: string | null };

/** Earlier policy versions come from the audit log (POLICY.UPDATED), since the policies API returns the active one only. */
export function policyHistory(rows: AuditRow[], purpose: string): PolicyVersion[] {
  return rows
    .filter((r) => r.action === "POLICY.UPDATED")
    .flatMap((r) => {
      const a = r.after as { purpose?: string; version?: number; allowed_fields?: string[]; note?: string } | null;
      return a && a.purpose === purpose && typeof a.version === "number"
        ? [{ id: r.id, version: a.version, allowed_fields: a.allowed_fields ?? [], note: a.note ?? null, at: r.occurred_at, actor_role: r.actor_role }]
        : [];
    })
    .sort((x, y) => y.version - x.version);
}
