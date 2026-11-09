import { describe, expect, it } from "vitest";
import en from "../i18n/en.json";
import {
  FIELDS, PURPOSES, consentStatus, fieldLabelKey, formatFieldValue, groupKid, refusalKey, validateConsent,
  validatePolicyNote, validateRegister, validateRequest, verifyUrl, verifyView,
} from "../consent";

const keys = en as Record<string, string>;

describe("verifyView", () => {
  it("maps the four statuses to an icon, tone and copy that exist", () => {
    for (const s of ["GENUINE", "EXPIRED", "REVOKED", "TAMPERED"]) {
      const v = verifyView(s);
      expect(v.status).toBe(s);
      expect(keys[v.titleKey]).toBeTruthy();
      expect(keys[v.bodyKey]).toBeTruthy();
    }
  });
  it("shows token details only when genuine", () => {
    expect(verifyView("GENUINE").showFields).toBe(true);
    expect(verifyView("EXPIRED").showFields).toBe(false);
    expect(verifyView("REVOKED").showFields).toBe(false);
  });
  it("shows nothing from the token when tampered, and fails closed for unknown input", () => {
    expect(verifyView("TAMPERED")).toMatchObject({ showFields: false, showMeta: false, tone: "excess" });
    expect(verifyView("SOMETHING_ELSE").status).toBe("TAMPERED");
  });
  it("keeps issuer and dates for expired and revoked, which are genuine but no longer valid", () => {
    expect(verifyView("EXPIRED").showMeta).toBe(true);
    expect(verifyView("REVOKED").showMeta).toBe(true);
  });
});

describe("fields", () => {
  it("has a label for every field and purpose", () => {
    for (const f of FIELDS) expect(keys[fieldLabelKey(f)]).toBeTruthy();
    for (const p of PURPOSES) {
      expect(keys[`purpose.${p}`]).toBeTruthy();
      expect(keys[`purpose.${p}.desc`]).toBeTruthy();
    }
  });
  it("formats values", () => {
    expect(formatFieldValue("year_of_study", 2)).toBe("2");
    expect(formatFieldValue("status", "pending_apaar")).toBe("pending apaar");
    expect(formatFieldValue("name", null)).toBe("-");
    expect(formatFieldValue("name", "Asha K")).toBe("Asha K");
  });
});

describe("refusalKey", () => {
  it("maps the two explicit reasons and sends everything else to the generic message", () => {
    expect(refusalKey("VERIFIER_NOT_APPROVED")).toBe("refusal.VERIFIER_NOT_APPROVED");
    expect(refusalKey("FIELD_NOT_ALLOWED_BY_POLICY")).toBe("refusal.FIELD_NOT_ALLOWED_BY_POLICY");
    expect(refusalKey("CONSENT_NOT_AVAILABLE")).toBe("refusal.CONSENT_NOT_AVAILABLE");
    expect(refusalKey("UNKNOWN_STUDENT")).toBe("refusal.UNKNOWN_STUDENT");
    expect(refusalKey("SOMETHING_NEW")).toBe("refusal.CONSENT_NOT_AVAILABLE");
    expect(refusalKey(null)).toBe("refusal.CONSENT_NOT_AVAILABLE");
    for (const r of ["NO_CONSENT", "EXPIRED", "WITHDRAWN", "PURPOSE_NOT_COVERED", "FIELD_NOT_IN_CONSENT"]) {
      expect(keys[refusalKey(r)]).toBeTruthy();
    }
  });
});

describe("validateRegister", () => {
  const ok = { org_name: "Acme Ltd", org_type: "EMPLOYER", contact: "A Person", email: "a@acme.test", password: "longenough1", purposes: ["EMPLOYMENT"] };
  it("accepts a complete form", () => expect(validateRegister(ok)).toEqual({}));
  it("flags each bad field with a message key", () => {
    const e = validateRegister({ ...ok, org_name: "A", org_type: "", contact: "", email: "nope", password: "short", purposes: [] });
    expect(Object.keys(e).sort()).toEqual(["contact", "email", "org_name", "org_type", "password", "purposes"]);
    for (const k of Object.values(e)) expect(keys[k]).toBeTruthy();
  });
  it("caps the password at 72 characters, the limit bcrypt honours", () => {
    expect(validateRegister({ ...ok, password: "x".repeat(73) }).password).toBeTruthy();
  });
});

describe("validateRequest", () => {
  it("needs an id, a purpose and at least one field", () => {
    expect(validateRequest({ apaar_id: " ", purpose: "", fields: [] })).toEqual({
      apaar_id: "val.apaar", purpose: "val.purpose", fields: "val.fields",
    });
    expect(validateRequest({ apaar_id: "9999 0000 0001", purpose: "EMPLOYMENT", fields: ["name"] })).toEqual({});
  });
});

describe("validateConsent", () => {
  const now = new Date("2026-01-01T00:00:00Z");
  const ok = { apaar_id: "999900000001", purposes: ["EMPLOYMENT"], fields: ["name"], source: "paper form", expires_at: "2026-06-01" };
  it("accepts a valid consent", () => expect(validateConsent(ok, now)).toEqual({}));
  it("rejects past or too-far expiry, and empty lists", () => {
    expect(validateConsent({ ...ok, expires_at: "2025-12-31" }, now).expires_at).toBe("val.expiryFuture");
    expect(validateConsent({ ...ok, expires_at: "2031-01-01" }, now).expires_at).toBe("val.expiryMax");
    expect(validateConsent({ ...ok, expires_at: "" }, now).expires_at).toBe("val.expiryFuture");
    const e = validateConsent({ ...ok, purposes: [], fields: [], source: " " }, now);
    expect(Object.keys(e).sort()).toEqual(["fields", "purposes", "source"]);
  });
});

describe("validatePolicyNote", () => {
  it("requires a note", () => {
    expect(validatePolicyNote("  ")).toBe("flag.note.required");
    expect(validatePolicyNote("tightened")).toBeNull();
  });
});

describe("consentStatus", () => {
  const now = new Date("2026-03-01T00:00:00Z");
  it("is withdrawn before expired before active", () => {
    expect(consentStatus({ withdrawn_at: "2026-02-01T00:00:00Z", expires_at: "2027-01-01T00:00:00Z" }, now)).toBe("withdrawn");
    expect(consentStatus({ withdrawn_at: "2026-02-01T00:00:00Z", expires_at: "2026-01-01T00:00:00Z" }, now)).toBe("withdrawn");
    expect(consentStatus({ withdrawn_at: null, expires_at: "2026-01-01T00:00:00Z" }, now)).toBe("expired");
    expect(consentStatus({ withdrawn_at: null, expires_at: "2026-03-01T00:00:00Z" }, now)).toBe("expired");
    expect(consentStatus({ withdrawn_at: null, expires_at: "2027-01-01T00:00:00Z" }, now)).toBe("active");
  });
});

describe("verifyUrl and groupKid", () => {
  it("builds the public check URL for the QR code", () => {
    expect(verifyUrl("https://hub.example/", "a.b.c")).toBe("https://hub.example/verify/a.b.c");
    expect(verifyUrl("http://localhost:3000", "a b")).toBe("http://localhost:3000/verify/a%20b");
  });
  it("groups a key id in fours", () => expect(groupKid("0123456789abcdef")).toBe("0123 4567 89ab cdef"));
});
