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

export const formatDateTime = (iso: string | null | undefined): string =>
  iso ? new Date(iso).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }) : "-";

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
