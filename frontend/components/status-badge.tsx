import { AlertTriangle, Ban, Check, CircleDot, Clock, Flag, XOctagon } from "lucide-react";
import { flagState, institutionState, recordStatus, type StatusMeta, type Tone } from "@/lib/status";

const ICONS = { check: Check, flag: Flag, clock: Clock, ban: Ban, alert: AlertTriangle, x: XOctagon, dot: CircleDot };
const TONES: Record<Tone, string> = {
  clear: "bg-status-clear-bg text-status-clear",
  alert: "bg-status-alert-bg text-status-alert",
  excess: "bg-status-excess-bg text-status-excess",
  neutral: "bg-muted text-muted-foreground",
};

export function ToneBadge({ meta, label }: { meta: StatusMeta; label: string }) {
  const Icon = ICONS[meta.icon];
  return (
    <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ${TONES[meta.tone]}`}>
      <Icon aria-hidden className="size-3.5" />
      {label}
    </span>
  );
}

export const StatusBadge = ({ status, label }: { status: string; label: string }) => (
  <ToneBadge meta={recordStatus(status)} label={label} />
);
export const InstitutionStateBadge = ({ state, label }: { state: string; label: string }) => (
  <ToneBadge meta={institutionState(state)} label={label} />
);

export const FlagStateBadge = ({ state, label }: { state: string; label: string }) => (
  <ToneBadge meta={flagState(state)} label={label} />
);
