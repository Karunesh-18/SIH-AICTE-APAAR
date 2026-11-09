import { describe, expect, it } from "vitest";
import { allowedActions, evidenceFacts, filtersFromQuery, filtersToQuery, formatAge, noteError, r05Sides } from "../review";

describe("allowedActions (mirrors backend domain/flags.py)", () => {
  it("open: review, resolve, dismiss, ask", () =>
    expect(allowedActions("open", "AICTE_OFFICER", "R06")).toEqual(["review", "resolve", "dismiss", "ask"]));
  it("under_review has no review", () =>
    expect(allowedActions("under_review", "AICTE_ADMIN", "R06")).toEqual(["resolve", "dismiss", "ask"]));
  it("ask_institution: review (back), resolve, dismiss", () =>
    expect(allowedActions("ask_institution", "AICTE_ADMIN", "R05")).toEqual(["review", "resolve", "dismiss"]));
  it("terminal states have none", () => {
    expect(allowedActions("resolved", "AICTE_ADMIN", "R06")).toEqual([]);
    expect(allowedActions("dismissed", "AICTE_OFFICER", "R06")).toEqual([]);
  });
  it("link only for R08", () => {
    expect(allowedActions("open", "AICTE_ADMIN", "R08")).toContain("link");
    expect(allowedActions("open", "AICTE_ADMIN", "R05")).not.toContain("link");
  });
  it("institution may only reply to an ask", () => {
    expect(allowedActions("ask_institution", "INSTITUTION_STAFF", "R05")).toEqual(["reply"]);
    expect(allowedActions("open", "INSTITUTION_ADMIN", "R05")).toEqual([]);
  });
  it("verifier none", () => expect(allowedActions("open", "VERIFIER", "R01")).toEqual([]));
});

describe("noteError", () => {
  it("requires a non-blank note", () => {
    expect(noteError("")).toBe("flag.note.required");
    expect(noteError("   \n")).toBe("flag.note.required");
    expect(noteError(" ok ")).toBeNull();
  });
});

describe("formatAge", () => {
  it("formats days", () => {
    expect(formatAge(0)).toEqual({ key: "age.today", n: 0 });
    expect(formatAge(1)).toEqual({ key: "age.day", n: 1 });
    expect(formatAge(5)).toEqual({ key: "age.days", n: 5 });
  });
});

describe("filters <-> query string", () => {
  it("round-trips and drops empties", () => {
    const f = filtersFromQuery(new URLSearchParams("state=open&rule=R06&age_days=7&institution=&offset=25"));
    expect(f).toEqual({ state: "open", rule: "R06", institution: "", region: "", age_days: "7", offset: 25 });
    expect(filtersToQuery(f)).toBe("state=open&rule=R06&age_days=7&offset=25");
  });
  it("ignores bad offset", () => expect(filtersFromQuery(new URLSearchParams("offset=-3")).offset).toBe(0));
});

describe("evidenceFacts", () => {
  it("R06 intake numbers, ordering flag", () => {
    const r = evidenceFacts("R06", { approved_intake: 60, supernumerary_seats: 6, allowed: 66, actual: 70, excess: 4, ordering_only: true });
    expect(r.facts.map((x) => [x.key, x.value])).toEqual([
      ["approved_intake", "60"], ["supernumerary_seats", "6"], ["allowed", "66"], ["actual", "70"], ["excess", "4"]]);
    expect(r.orderingOnly).toBe(true);
  });
  it("R03 shows submitted vs registry", () => {
    const r = evidenceFacts("R03", { submitted: "A Kumar", registry: "Anil Kumar", similarity: 0.5, threshold: 0.8 });
    expect(r.facts.map((x) => x.key)).toEqual(["submitted", "registry", "similarity", "threshold"]);
  });
  it("R04 count, R02 found", () => {
    expect(evidenceFacts("R04", { apaar_id: "x", count: 2 }).facts.find((f) => f.key === "count")?.value).toBe("2");
    expect(evidenceFacts("R02", { found: "123", expected_digits: 12, checksum: "none", digits_found: 3 }).facts.length).toBe(4);
  });
  it("R05 leaves elsewhere/this to r05Sides", () => {
    const ev = { apaar_id: "9999****", this: { programme: "BE", admission_date: "2025-08-01" },
      elsewhere: [{ institution: "B", programme: "MBA", admission_date: "2025-08-02" }] };
    expect(evidenceFacts("R05", ev).facts.map((f) => f.key)).toEqual(["apaar_id"]);
    expect(r05Sides(ev)).toEqual({
      here: { programme: "BE", admission_date: "2025-08-01" },
      elsewhere: [{ institution: "B", programme: "MBA", admission_date: "2025-08-02" }] });
  });
  it("unknown rule falls back to scalar entries", () =>
    expect(evidenceFacts("R99", { a: 1, b: "x", c: { d: 1 } }).facts.map((f) => f.key)).toEqual(["a", "b"]));
});
