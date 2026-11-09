import { describe, expect, it } from "vitest";
import {
  countdown, csvFilename, fmtInt, fmtPct, intakeBars, ruleColor, ruleStack, reportQuery, clockLabel,
  ladderValid, toLocalInput, fromLocalInput,
} from "../dash";

describe("intakeBars", () => {
  const rows = [
    { id: "a", name: "A", enrolled: 90, allowed: 100 },
    { id: "b", name: "B", enrolled: 120, allowed: 100 },
    { id: "c", name: "C", enrolled: 100, allowed: 100 },
  ];
  it("splits into within, headroom and over, excess first", () => {
    const b = intakeBars(rows);
    expect(b.map((x) => x.id)).toEqual(["b", "c", "a"]);
    expect(b[0]).toMatchObject({ within: 100, headroom: 0, over: 20, excess: true });
    expect(b[2]).toMatchObject({ within: 90, headroom: 10, over: 0, excess: false });
  });
  it("at the cap is not excess", () => {
    expect(intakeBars(rows).find((x) => x.id === "c")?.excess).toBe(false);
  });
});

describe("ruleStack", () => {
  const rows = [
    { month: "2026-10", rule: "R03", count: 2 },
    { month: "2026-10", rule: "R10", count: 1 },
    { month: "2026-11", rule: "R03", count: 4 },
    { month: "2026-11", rule: "R11", count: 3 },
  ];
  it("pivots by month and folds R09+ into other", () => {
    const s = ruleStack(rows);
    expect(s.data).toEqual([
      { month: "2026-10", R03: 2, other: 1 },
      { month: "2026-11", R03: 4, other: 3 },
    ]);
    expect(s.keys).toEqual(["R03", "other"]);
  });
  it("gives each rule its own fixed slot, other is neutral", () => {
    expect(ruleColor("R01")).toBe("var(--chart-1)");
    expect(ruleColor("R08")).toBe("var(--chart-8)");
    expect(ruleColor("other")).toBe("var(--chart-other)");
  });
});

describe("format", () => {
  it("formats numbers", () => {
    expect(fmtInt(12345)).toBe("12,345");
    expect(fmtPct(3.14159)).toBe("3.1%");
  });
});

describe("countdown", () => {
  const now = new Date("2026-11-09T00:00:00Z");
  it("counts days and hours to close", () => {
    expect(countdown("2026-11-11T05:00:00Z", now)).toEqual({ state: "open", days: 2, hours: 5 });
  });
  it("reports closed with time since", () => {
    expect(countdown("2026-11-08T22:00:00Z", now)).toEqual({ state: "closed", days: 0, hours: 2 });
  });
});

describe("csv helpers", () => {
  it("names the file and builds the query", () => {
    expect(csvFilename("late_submitters")).toBe("late_submitters.csv");
    expect(reportQuery({ region: "N", type: "", cycle_year: "2026" }, "csv")).toBe("format=csv&region=N&cycle_year=2026");
    expect(reportQuery({}, "json")).toBe("format=json");
  });
});

describe("clock label", () => {
  it("is null at zero and signed otherwise", () => {
    expect(clockLabel(0)).toBeNull();
    expect(clockLabel(3)).toBe("+3");
    expect(clockLabel(-1.5)).toBe("-1.5");
  });
});

describe("window form", () => {
  it("validates ladder step names", () => {
    expect(ladderValid([{ step: "a", offset_hours: -24, audience: "institution" }])).toBe(true);
    expect(ladderValid([{ step: "a", offset_hours: 0, audience: "admin" }, { step: "a", offset_hours: 1, audience: "admin" }])).toBe(false);
    expect(ladderValid([{ step: " ", offset_hours: 0, audience: "admin" }])).toBe(false);
  });
  it("round-trips datetime-local", () => {
    expect(fromLocalInput(toLocalInput("2026-11-09T10:30:00Z"))).toBe("2026-11-09T10:30:00.000Z");
  });
});
