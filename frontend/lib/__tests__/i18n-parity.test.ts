import { describe, expect, it } from "vitest";
import en from "../i18n/en.json";
import hi from "../i18n/hi.json";

describe("i18n", () => {
  it("has every English key in Hindi and vice versa", () => {
    expect(Object.keys(hi).sort()).toEqual(Object.keys(en).sort());
  });
});
