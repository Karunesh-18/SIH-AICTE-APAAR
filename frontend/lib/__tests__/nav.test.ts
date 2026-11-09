import { describe, expect, it } from "vitest";
import { navFor } from "../nav";

describe("navFor", () => {
  it("gives verifiers only the verifier page", () => {
    expect(navFor("VERIFIER").map((n) => n.href)).toEqual(["/verifier"]);
  });
  it("gives admins the rules page, officers not", () => {
    expect(navFor("AICTE_ADMIN").some((n) => n.href === "/admin/rules")).toBe(true);
    expect(navFor("AICTE_OFFICER").some((n) => n.href === "/admin/rules")).toBe(false);
  });
});

describe("reports nav", () => {
  it("is offered to AICTE and institution roles but not verifiers", () => {
    for (const r of ["AICTE_ADMIN", "AICTE_OFFICER", "INSTITUTION_ADMIN", "INSTITUTION_STAFF"] as const)
      expect(navFor(r).some((n) => n.href === "/reports")).toBe(true);
    expect(navFor("VERIFIER").some((n) => n.href === "/reports")).toBe(false);
  });
});
