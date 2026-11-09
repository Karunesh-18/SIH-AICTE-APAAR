import { describe, expect, it } from "vitest";
import { staffPath, userFormErrors } from "../users";

const ok = { email: "a@b.test", full_name: "Asha", role: "AICTE_OFFICER", institution_id: "", regions: [] };

describe("userFormErrors", () => {
  it("passes a valid officer", () => expect(userFormErrors(ok, "admin")).toEqual({}));
  it("needs a plausible email and a name", () => {
    expect(userFormErrors({ ...ok, email: "nope", full_name: " " }, "admin")).toEqual({
      email: "users.err.email", full_name: "users.err.name",
    });
  });
  it("institution roles need an institution (admin form only)", () => {
    expect(userFormErrors({ ...ok, role: "INSTITUTION_STAFF" }, "admin")).toEqual({ institution_id: "users.err.institution" });
    expect(userFormErrors({ ...ok, role: "INSTITUTION_STAFF" }, "staff")).toEqual({});
  });
  it("a password, if given, is at least 8 characters", () => {
    expect(userFormErrors({ ...ok, password: "short" }, "admin")).toEqual({ password: "users.err.password" });
    expect(userFormErrors({ ...ok, password: "longenough1" }, "admin")).toEqual({});
  });
});

describe("staffPath", () => {
  it("builds the institution staff routes", () => {
    expect(staffPath("i1")).toBe("/institutions/i1/staff");
    expect(staffPath("i1", "u1", "reset-password")).toBe("/institutions/i1/staff/u1/reset-password");
  });
});
