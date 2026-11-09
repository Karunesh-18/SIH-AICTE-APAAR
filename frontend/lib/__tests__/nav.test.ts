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
