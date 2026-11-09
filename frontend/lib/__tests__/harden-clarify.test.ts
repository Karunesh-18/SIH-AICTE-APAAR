import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { demoEnabled } from "../demo";
import en from "../i18n/en.json";
import hi from "../i18n/hi.json";

const root = join(__dirname, "..", "..");
const src = (p: string) => readFileSync(join(root, p), "utf8");

describe("demo flag", () => {
  it("is off unless exactly '1'", () => {
    expect(demoEnabled(undefined)).toBe(false);
    expect(demoEnabled("")).toBe(false);
    expect(demoEnabled("0")).toBe(false);
    expect(demoEnabled("true")).toBe(false);
    expect(demoEnabled("1")).toBe(true);
  });
  it("login uses demoEnabled, not a negative default", () => {
    expect(src("app/login/page.tsx")).not.toMatch(/NEXT_PUBLIC_DEMO !== /);
  });
});

describe("no hardcoded UI strings", () => {
  const login = src("app/login/page.tsx");
  const reports = src("app/(app)/reports/page.tsx");
  it("login routes network error and demo roles through t()", () => {
    expect(login).not.toContain("Could not reach the server");
    for (const s of ["AICTE admin", "AICTE officer", "Institution admin", "Institution staff", '"Verifier"'])
      expect(login, s).not.toContain(s);
  });
  it("reports has no English programme literals", () => {
    for (const s of ["ENGINEERING", "MANAGEMENT", "PHARMACY"]) expect(reports, s).not.toContain(s);
  });
  it("new keys exist in en and hi", () => {
    for (const k of ["auth.networkError", "auth.demoOnly", "reports.sectionReport", "reports.sectionFilters", "reports.reset", "brand.tagline"]) {
      expect(en, k).toHaveProperty([k]);
      expect(hi, k).toHaveProperty([k]);
    }
  });
});
