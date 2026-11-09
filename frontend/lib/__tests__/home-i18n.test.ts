import { describe, expect, it } from "vitest";
import { homeFor, navFor, type Role } from "../nav";
import { t } from "../i18n";
import en from "../i18n/en.json";
import hi from "../i18n/hi.json";

const roles: Role[] = ["AICTE_ADMIN", "AICTE_OFFICER", "INSTITUTION_ADMIN", "INSTITUTION_STAFF", "VERIFIER"];

describe("homeFor", () => {
  it("is the first nav route of every role", () => {
    for (const r of roles) expect(homeFor(r)).toBe(navFor(r)[0].href);
  });
});

describe("t()", () => {
  it("returns the Hindi string when present, English otherwise, key as last resort", () => {
    expect(t("hi", "nav.dashboard")).toBe(hi["nav.dashboard" as keyof typeof hi]);
    expect(t("en", "nav.dashboard")).toBe(en["nav.dashboard" as keyof typeof en]);
    expect(t("hi", "no.such.key")).toBe("no.such.key");
  });
  it("every nav key used by any role exists in English", () => {
    for (const r of roles) for (const n of navFor(r)) expect(en).toHaveProperty([n.key]);
  });
  it("Hindi never has a key English lacks", () => {
    for (const k of Object.keys(hi)) expect(en).toHaveProperty([k]);
  });
});
