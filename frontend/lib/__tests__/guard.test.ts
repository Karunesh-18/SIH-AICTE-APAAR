import { describe, expect, it } from "vitest";
import { allowed, errorKey } from "../guard";
import { ApiError } from "../api";

describe("guard", () => {
  it("allows listed roles only", () => {
    expect(allowed("INSTITUTION_ADMIN", ["INSTITUTION_ADMIN"])).toBe(true);
    expect(allowed("INSTITUTION_STAFF", ["INSTITUTION_ADMIN"])).toBe(false);
    expect(allowed(undefined, ["AICTE_ADMIN"])).toBe(false);
  });
  it("maps API errors to message keys", () => {
    expect(errorKey(new ApiError(403, "x"))).toBe("error.forbidden");
    expect(errorKey(new ApiError(404, "x"))).toBe("error.notFound");
    expect(errorKey(new Error("x"))).toBe("error.generic");
  });
});
