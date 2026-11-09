// Pure logic for consent and verification screens. Mirrors backend/app/models/consent.py and
// backend/app/domain/consent.py; the server still decides everything.
export const PURPOSES = ["EMPLOYMENT", "HIGHER_EDUCATION", "REGULATORY", "SCHOLARSHIP"] as const;
export const FIELDS = ["name", "programme", "status", "level", "year_of_study", "admission_category"] as const;
export const ORG_TYPES = ["EMPLOYER", "INSTITUTION", "REGULATOR", "OTHER"] as const;

export type VerifyStatus = "GENUINE" | "EXPIRED" | "REVOKED" | "TAMPERED";
export type VerifyView = {
  status: VerifyStatus; tone: "clear" | "alert" | "excess"; icon: "check" | "clock" | "ban" | "alert";
  titleKey: string; bodyKey: string; showFields: boolean; showMeta: boolean;
};

const VIEWS: Record<VerifyStatus, VerifyView> = {
  GENUINE: { status: "GENUINE", tone: "clear", icon: "check", titleKey: "verify.genuine", bodyKey: "verify.genuine.body", showFields: true, showMeta: true },
  EXPIRED: { status: "EXPIRED", tone: "alert", icon: "clock", titleKey: "verify.expired", bodyKey: "verify.expired.body", showFields: false, showMeta: true },
  REVOKED: { status: "REVOKED", tone: "alert", icon: "ban", titleKey: "verify.revoked", bodyKey: "verify.revoked.body", showFields: false, showMeta: true },
  TAMPERED: { status: "TAMPERED", tone: "excess", icon: "alert", titleKey: "verify.tampered", bodyKey: "verify.tampered.body", showFields: false, showMeta: false },
};
/** Anything the page does not recognise is shown as unverifiable, never as genuine. */
export const verifyView = (status: string): VerifyView => VIEWS[status as VerifyStatus] ?? VIEWS.TAMPERED;

export const fieldLabelKey = (f: string) => `field.${f}`;
export function formatFieldValue(_field: string, v: unknown): string {
  if (v === null || v === undefined || v === "") return "-";
  return typeof v === "string" ? v.replace(/_/g, " ") : String(v);
}

const REASONS = ["CONSENT_NOT_AVAILABLE", "VERIFIER_NOT_APPROVED", "FIELD_NOT_ALLOWED_BY_POLICY", "NO_CONSENT", "EXPIRED",
  "WITHDRAWN", "PURPOSE_NOT_COVERED", "FIELD_NOT_IN_CONSENT", "UNKNOWN_STUDENT"];
/** A verifier only ever receives the generic or the two explicit reasons; anything else falls back to generic. */
export const refusalKey = (reason: string | null | undefined): string =>
  `refusal.${reason && REASONS.includes(reason) ? reason : "CONSENT_NOT_AVAILABLE"}`;

type Errors = Record<string, string>;
const trimmed = (s: string) => s.trim();

export type RegisterForm = { org_name: string; org_type: string; contact: string; email: string; password: string; purposes: string[] };
export function validateRegister(f: RegisterForm): Errors {
  const e: Errors = {};
  if (trimmed(f.org_name).length < 2) e.org_name = "val.orgName";
  if (!(ORG_TYPES as readonly string[]).includes(f.org_type)) e.org_type = "val.orgType";
  if (trimmed(f.contact).length < 2) e.contact = "val.contact";
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(trimmed(f.email))) e.email = "val.email";
  if (f.password.length < 10) e.password = "val.passwordShort";
  else if (f.password.length > 72) e.password = "val.passwordLong";
  if (f.purposes.length === 0) e.purposes = "val.purposes";
  return e;
}

export type RequestForm = { apaar_id: string; purpose: string; fields: string[] };
export function validateRequest(f: RequestForm): Errors {
  const e: Errors = {};
  if (!trimmed(f.apaar_id)) e.apaar_id = "val.apaar";
  if (!f.purpose) e.purpose = "val.purpose";
  if (f.fields.length === 0) e.fields = "val.fields";
  return e;
}

export type ConsentForm = { apaar_id: string; purposes: string[]; fields: string[]; source: string; expires_at: string };
const MAX_DAYS = 3 * 366; // backend/app/services/consents.py MAX_VALID_DAYS
export function validateConsent(f: ConsentForm, now: Date): Errors {
  const e: Errors = {};
  if (!trimmed(f.apaar_id)) e.apaar_id = "val.apaar";
  if (f.purposes.length === 0) e.purposes = "val.purposes";
  if (f.fields.length === 0) e.fields = "val.fields";
  if (!trimmed(f.source)) e.source = "val.source";
  const exp = new Date(f.expires_at);
  if (!f.expires_at || Number.isNaN(exp.getTime()) || exp <= now) e.expires_at = "val.expiryFuture";
  else if (exp.getTime() > now.getTime() + MAX_DAYS * 86_400_000) e.expires_at = "val.expiryMax";
  return e;
}

export const validatePolicyNote = (note: string): string | null => (trimmed(note) ? null : "flag.note.required");

export type ConsentStatus = "active" | "expired" | "withdrawn";
export function consentStatus(c: { withdrawn_at: string | null; expires_at: string }, now: Date): ConsentStatus {
  if (c.withdrawn_at) return "withdrawn";
  return new Date(c.expires_at) <= now ? "expired" : "active";
}

export const verifyUrl = (origin: string, token: string) => `${origin.replace(/\/+$/, "")}/verify/${encodeURIComponent(token)}`;
export const groupKid = (kid: string) => kid.replace(/(.{4})(?=.)/g, "$1 ");
