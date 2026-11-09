export type Tone = "clear" | "alert" | "excess" | "neutral";
export type StatusMeta = { labelKey: string; icon: "check" | "flag" | "clock" | "ban" | "alert" | "x" | "dot"; tone: Tone };

const RECORD: Record<string, StatusMeta> = {
  valid: { labelKey: "status.valid", icon: "check", tone: "clear" },
  flagged: { labelKey: "status.flagged", icon: "flag", tone: "alert" },
  pending_apaar: { labelKey: "status.pending_apaar", icon: "clock", tone: "alert" },
  withdrawn: { labelKey: "status.withdrawn", icon: "ban", tone: "neutral" },
  submitted: { labelKey: "status.submitted", icon: "dot", tone: "neutral" },
};
export const recordStatus = (s: string): StatusMeta =>
  RECORD[s] ?? { labelKey: `status.${s}`, icon: "dot", tone: "neutral" };

const INST: Record<string, StatusMeta> = {
  Clear: { labelKey: "state.Clear", icon: "check", tone: "clear" },
  Alert: { labelKey: "state.Alert", icon: "alert", tone: "alert" },
  Excess: { labelKey: "state.Excess", icon: "x", tone: "excess" },
};
export const institutionState = (s: string): StatusMeta =>
  INST[s] ?? { labelKey: `state.${s}`, icon: "dot", tone: "neutral" };

export const formatDateTime = (iso: string | null | undefined, lang: "en" | "hi" = "en"): string =>
  iso ? new Date(iso).toLocaleString(lang === "hi" ? "hi-IN" : "en-IN", { dateStyle: "medium", timeStyle: "short" }) : "-";

/** Region names come from the API in English; translate the known ones. */
export const regionLabel = (t: (k: string) => string, name: string): string => {
  const v = t(`region.${name}`);
  return v === `region.${name}` ? name : v;
};

export const isMasked = (v: string | null | undefined): boolean => !!v && v.includes("*");

const FLAG: Record<string, StatusMeta> = {
  open: { labelKey: "flag.state.open", icon: "flag", tone: "alert" },
  under_review: { labelKey: "flag.state.under_review", icon: "clock", tone: "neutral" },
  ask_institution: { labelKey: "flag.state.ask_institution", icon: "alert", tone: "alert" },
  resolved: { labelKey: "flag.state.resolved", icon: "check", tone: "clear" },
  dismissed: { labelKey: "flag.state.dismissed", icon: "ban", tone: "neutral" },
};
export const flagState = (s: string): StatusMeta =>
  FLAG[s] ?? { labelKey: `flag.state.${s}`, icon: "dot", tone: "neutral" };

const CONSENT: Record<string, StatusMeta> = {
  active: { labelKey: "consent.status.active", icon: "check", tone: "clear" },
  expired: { labelKey: "consent.status.expired", icon: "clock", tone: "neutral" },
  withdrawn: { labelKey: "consent.status.withdrawn", icon: "ban", tone: "neutral" },
};
export const consentMeta = (s: string): StatusMeta => CONSENT[s] ?? { labelKey: `consent.status.${s}`, icon: "dot", tone: "neutral" };

/** Outcome of a verification request; a revoked grant reads as Revoked. */
export function outcomeMeta(outcome: string, revokedAt: string | null): StatusMeta {
  if (revokedAt) return { labelKey: "outcome.REVOKED", icon: "ban", tone: "alert" };
  if (outcome === "GRANTED") return { labelKey: "outcome.GRANTED", icon: "check", tone: "clear" };
  return { labelKey: "outcome.REFUSED", icon: "x", tone: "excess" };
}
