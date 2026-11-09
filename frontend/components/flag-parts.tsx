"use client";
import { Masked } from "@/components/masked";
import { FlagStateBadge } from "@/components/status-badge";
import { useAuth } from "@/lib/auth";
import { formatDateTime } from "@/lib/status";
import { evidenceFacts, formatAge, r05Sides } from "@/lib/review";
import type { FlagDetail, FlagEvent, RecordRow } from "@/lib/types";

export function RuleChip({ code }: { code: string }) {
  const { t } = useAuth();
  return (
    <span title={t(`rule.${code}`)} className="inline-flex items-center gap-1.5 text-sm">
      <span className="rounded bg-status-alert-bg px-1.5 py-0.5 font-mono text-xs text-status-alert">{code}</span>
      <span className="hidden lg:inline">{t(`rule.${code}`)}</span>
    </span>
  );
}

export function Age({ days }: { days: number }) {
  const { t } = useAuth();
  const a = formatAge(days);
  return <span className="tabular-nums">{a.key === "age.days" ? `${a.n} ${t(a.key)}` : t(a.key)}</span>;
}

export const StateBadge = ({ state }: { state: string }) => {
  const { t } = useAuth();
  return <FlagStateBadge state={state} label={t(`flag.state.${state}`)} />;
};

function Facts({ items }: { items: { key: string; value: string }[] }) {
  const { t } = useAuth();
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-sm tabular-nums">
      {items.map((f) => (
        <div key={f.key} className="contents">
          <dt className="text-muted-foreground">{t(`ev.${f.key}`)}</dt>
          <dd className="font-mono">{f.value}</dd>
        </div>
      ))}
    </dl>
  );
}

const rowLine = (r: RecordRow) => `${r.row_number}`;

/** Evidence as numbers per rule; R04 and R05 get side-by-side panels. */
export function Evidence({ flag }: { flag: Pick<FlagDetail, "rule_code" | "evidence" | "records"> }) {
  const { t } = useAuth();
  const { facts, orderingOnly } = evidenceFacts(flag.rule_code, flag.evidence);
  const sides = flag.rule_code === "R05" ? r05Sides(flag.evidence) : null;
  const m = t("record.masked");
  return (
    <div className="flex flex-col gap-4">
      <Facts items={facts} />
      {flag.rule_code === "R03" && facts.some((f) => f.key === "registry") && (
        <div className="grid max-w-md grid-cols-2 gap-3 text-sm">
          {(["submitted", "registry"] as const).map((k) => (
            <div key={k} className="rounded-md border border-border p-3">
              <p className="text-xs text-muted-foreground">{t(`ev.${k}`)}</p>
              <p className="mt-1 font-medium">{String(flag.evidence[k])}</p>
            </div>
          ))}
        </div>
      )}
      {orderingOnly && <p className="text-sm text-muted-foreground">{t("flag.r06.ordering")}</p>}
      {sides && (
        <div className="grid gap-3 sm:grid-cols-2">
          {sides.here && <SidePanel title={t("ev.here")} s={sides.here} />}
          {sides.elsewhere.map((s, i) => <SidePanel key={i} title={`${t("ev.elsewhere")} ${s.institution ?? ""}`} s={s} />)}
        </div>
      )}
      {flag.rule_code === "R04" && flag.records.length > 0 && (
        <div>
          <p className="mb-2 text-sm text-muted-foreground">{t("ev.dups")}</p>
          <div className="grid gap-3 sm:grid-cols-2">
            {flag.records.map((r) => (
              <div key={r.id} className="rounded-md border border-border p-3 text-sm">
                <p className="font-medium tabular-nums">{t("record.row")} {rowLine(r)}</p>
                <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-4 gap-y-0.5">
                  <dt className="text-muted-foreground">{t("record.name")}</dt><dd><Masked value={r.name} label={m} /></dd>
                  <dt className="text-muted-foreground">{t("record.dob")}</dt><dd><Masked value={r.dob} label={m} /></dd>
                  <dt className="text-muted-foreground">{t("record.programme")}</dt><dd>{r.programme}</dd>
                  <dt className="text-muted-foreground">{t("record.admission")}</dt><dd className="tabular-nums">{r.admission_date}</dd>
                </dl>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function SidePanel({ title, s }: { title: string; s: { programme: string; admission_date: string | null } }) {
  const { t } = useAuth();
  return (
    <div className="rounded-md border border-border p-3 text-sm">
      <p className="font-medium">{title}</p>
      <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-4 gap-y-0.5">
        <dt className="text-muted-foreground">{t("ev.programme")}</dt><dd>{s.programme}</dd>
        <dt className="text-muted-foreground">{t("ev.admitted")}</dt><dd className="tabular-nums">{s.admission_date ?? "-"}</dd>
      </dl>
    </div>
  );
}

export function RecordList({ records }: { records: RecordRow[] }) {
  const { t } = useAuth();
  const m = t("record.masked");
  if (records.length === 0) return <p className="text-sm text-muted-foreground">{t("flag.noRecords")}</p>;
  return (
    <ul className="flex flex-col divide-y divide-border rounded-md border border-border text-sm">
      {records.map((r) => (
        <li key={r.id} className="grid grid-cols-2 gap-x-4 gap-y-1 p-3 sm:grid-cols-5 tabular-nums">
          <span><Masked value={r.name} label={m} /></span>
          <span><Masked value={r.apaar_id} label={m} /></span>
          <span>{r.programme}</span>
          <span>{r.admission_date}</span>
          <span className="text-muted-foreground">{t("record.row")} {r.row_number}</span>
        </li>
      ))}
    </ul>
  );
}

export function Timeline({ events }: { events: FlagEvent[] }) {
  const { t } = useAuth();
  if (events.length === 0) return <p className="text-sm text-muted-foreground">{t("flag.noHistory")}</p>;
  return (
    <ol className="flex flex-col gap-3 border-l border-border pl-4">
      {events.map((e) => (
        <li key={e.id} className="text-sm">
          <p className="flex flex-wrap items-center gap-2">
            <StateBadge state={e.to_state} />
            <span className="font-medium">{e.actor_name}</span>
            <span className="text-muted-foreground tabular-nums">{formatDateTime(e.at)}</span>
          </p>
          {e.note && <p className="mt-1 whitespace-pre-wrap">{e.note}</p>}
        </li>
      ))}
    </ol>
  );
}
