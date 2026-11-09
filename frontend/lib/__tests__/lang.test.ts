import { describe, expect, it } from "vitest";
import { parseLang, resolveLang } from "../lang";

describe("parseLang", () => {
  it("accepts only en or hi", () => {
    expect(parseLang("hi")).toBe("hi");
    expect(parseLang("en")).toBe("en");
    expect(parseLang("fr")).toBeNull();
    expect(parseLang(null)).toBeNull();
    expect(parseLang(undefined)).toBeNull();
  });
});

describe("resolveLang", () => {
  it("signed-in users use their saved language", () => {
    expect(resolveLang("hi", "en")).toBe("hi");
  });
  it("public pages use the local choice, then English", () => {
    expect(resolveLang(undefined, "hi")).toBe("hi");
    expect(resolveLang(undefined, null)).toBe("en");
  });
});
