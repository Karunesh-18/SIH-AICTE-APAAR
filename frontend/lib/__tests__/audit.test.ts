import { describe, expect, it } from "vitest";
import { filterAudit, policyHistory } from "../audit";
import type { AuditRow } from "../types";

const row = (id: number, o: Partial<AuditRow>): AuditRow => ({
  id, occurred_at: "2026-03-10T10:00:00Z", actor_id: null, actor_role: "AICTE_ADMIN", action: "RECORD.VIEWED",
  entity_type: "record", entity_id: "x", before: null, after: null, ...o,
});
const rows = [
  row(1, {}),
  row(2, { actor_role: "VERIFIER", action: "VERIFICATION.GRANTED", entity_type: "verification_request" }),
  row(3, { occurred_at: "2026-03-12T10:00:00Z", action: "POLICY.UPDATED", entity_type: "purpose_policy",
    after: { purpose: "EMPLOYMENT", version: 2, allowed_fields: ["name"], note: "tighter" } }),
];

describe("filterAudit", () => {
  it("returns everything for empty filters", () => expect(filterAudit(rows, {})).toHaveLength(3));
  it("filters by role, action substring (case-insensitive) and entity", () => {
    expect(filterAudit(rows, { role: "VERIFIER" }).map((r) => r.id)).toEqual([2]);
    expect(filterAudit(rows, { action: "policy" }).map((r) => r.id)).toEqual([3]);
    expect(filterAudit(rows, { entity: "record" }).map((r) => r.id)).toEqual([1]);
  });
  it("filters by inclusive date range", () => {
    expect(filterAudit(rows, { from: "2026-03-11" }).map((r) => r.id)).toEqual([3]);
    expect(filterAudit(rows, { to: "2026-03-10" }).map((r) => r.id)).toEqual([1, 2]);
  });
});

describe("policyHistory", () => {
  it("lists POLICY.UPDATED entries for one purpose, newest version first", () => {
    const more = [...rows, row(4, { action: "POLICY.UPDATED", after: { purpose: "EMPLOYMENT", version: 3, allowed_fields: [], note: "n" } }),
      row(5, { action: "POLICY.UPDATED", after: { purpose: "SCHOLARSHIP", version: 2, allowed_fields: ["name"], note: "n" } })];
    expect(policyHistory(more, "EMPLOYMENT").map((h) => h.version)).toEqual([3, 2]);
    expect(policyHistory(more, "REGULATORY")).toEqual([]);
  });
});
