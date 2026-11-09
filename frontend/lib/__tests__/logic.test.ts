import { describe, expect, it } from "vitest";
import { formatDateTime, isMasked, recordStatus, institutionState } from "../status";
import { validateUploadFile, formatFromName, MAX_UPLOAD_BYTES } from "../upload-file";
import { pollInterval } from "../poll";
import { diffVersions, parseParams } from "../rules";
import { explainFlag, evidenceLines } from "../flags";

describe("recordStatus", () => {
  it("maps every status to a label key, icon and tone", () => {
    for (const s of ["valid", "flagged", "pending_apaar", "withdrawn", "submitted"] as const) {
      const m = recordStatus(s);
      expect(m.labelKey).toBe(`status.${s}`);
      expect(m.icon).toBeTruthy();
    }
    expect(recordStatus("flagged").tone).toBe("alert");
    expect(recordStatus("valid").tone).toBe("clear");
  });
  it("falls back for unknown", () => expect(recordStatus("zzz").tone).toBe("neutral"));
  it("maps institution states", () => {
    expect(institutionState("Excess").tone).toBe("excess");
    expect(institutionState("Clear").icon).not.toBe(institutionState("Alert").icon);
  });
});

describe("formatters", () => {
  it("formats dates and tolerates null", () => {
    expect(formatDateTime(null)).toBe("-");
    expect(formatDateTime("2026-03-01T10:00:00Z")).toMatch(/2026/);
  });
  it("detects masked values", () => {
    expect(isMasked("R*** K****")).toBe(true);
    expect(isMasked("2004-**-**")).toBe(true);
    expect(isMasked("Ravi")).toBe(false);
  });
});

describe("validateUploadFile", () => {
  const f = (name: string, size = 10) => ({ name, size });
  it("accepts allowed types", () => {
    for (const n of ["a.csv", "a.XLSX", "a.xls", "a.json"]) expect(validateUploadFile(f(n))).toBeNull();
  });
  it("rejects other types, empty and big files", () => {
    expect(validateUploadFile(f("a.pdf"))).toBe("upload.err.type");
    expect(validateUploadFile(f("a.csv", 0))).toBe("upload.err.empty");
    expect(validateUploadFile(f("a.csv", MAX_UPLOAD_BYTES + 1))).toBe("upload.err.size");
  });
  it("derives format from the name", () => {
    expect(formatFromName("x.xlsx")).toBe("xlsx");
    expect(formatFromName("x.txt")).toBeNull();
  });
});

describe("pollInterval", () => {
  it("polls while processing and stops when finished or unknown", () => {
    expect(pollInterval("RECEIVED")).toBeGreaterThan(0);
    expect(pollInterval("PROCESSING")).toBeGreaterThan(0);
    expect(pollInterval(undefined)).toBeGreaterThan(0);
    expect(pollInterval("DONE")).toBe(false);
    expect(pollInterval("REJECTED")).toBe(false);
  });
});

describe("rules helpers", () => {
  it("parses params and rejects non-objects", () => {
    expect(parseParams('{"a":1}')).toEqual({ ok: true, value: { a: 1 } });
    expect(parseParams("[1]").ok).toBe(false);
    expect(parseParams("{bad").ok).toBe(false);
  });
  it("diffs two versions on editable fields only", () => {
    const a = { version_no: 1, enabled: true, params: { x: 1 }, hard_stop: false, message_en: "m", message_hi: null };
    const b = { ...a, version_no: 2, params: { x: 2 } };
    expect(diffVersions(a, b).map((d) => d.field)).toEqual(["params"]);
    expect(diffVersions(a, a)).toEqual([]);
  });
});

describe("flags", () => {
  const r06 = { id: "1", rule_code: "R06", reason_key: "intake_cap", reason: "Over.", rows: [9, 10],
    evidence: { approved_intake: 10, supernumerary_seats: 1, allowed: 11, actual: 13, excess: 2, ordering_only: true } };
  it("lists evidence numbers", () => {
    const lines = evidenceLines(r06.evidence);
    expect(lines).toContainEqual({ key: "approved_intake", value: "10" });
    expect(lines).toContainEqual({ key: "excess", value: "2" });
  });
  it("explains R06 as ordering only and names rows", () => {
    const e = explainFlag(r06);
    expect(e.code).toBe("R06");
    expect(e.note).toBe("flag.r06.ordering");
    expect(e.rows).toBe("9, 10");
  });
  it("flattens nested evidence safely", () => {
    const l = evidenceLines({ elsewhere: [{ institution: "N", programme: "B", admission_date: "2025-01-01" }] });
    expect(l[0].value).toContain("N");
  });
});
