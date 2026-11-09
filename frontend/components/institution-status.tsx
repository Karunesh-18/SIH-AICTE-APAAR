"use client";
import Link from "next/link";
import { CalendarClock } from "lucide-react";
import { QueryError } from "@/components/query-error";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/auth";
import { countdown } from "@/lib/dash";
import { formatDateTime } from "@/lib/status";
import type { InstitutionDashboard, TodoFlag } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";

function Todo({ title, items, href }: { title: string; items: TodoFlag[]; href: string }) {
  if (!items.length) return null;
  return (
    <li>
      <p className="font-medium">{title} <span className="tabular-nums text-muted-foreground">({items.length})</span></p>
      <ul className="mt-1 flex flex-col gap-1 text-sm">
        {items.map((f) => (
          <li key={f.id}>
            <Link className="underline-offset-2 hover:underline" href={`${href}/${f.id}`}>
              <span className="font-mono text-xs">{f.rule}</span> {f.reason}
            </Link>
          </li>
        ))}
      </ul>
    </li>
  );
}

export function InstitutionStatus() {
  const { t } = useAuth();
  const q = useApiQuery<InstitutionDashboard>("/dashboards/institution");
  if (q.isPending) return <Skeleton className="mb-6 h-32 w-full max-w-xl" />;
  if (q.isError) return <div className="mb-6"><QueryError error={q.error} onRetry={() => q.refetch()} /></div>;
  const d = q.data;
  const w = d.window;
  const c = w && countdown(w.closes_at);
  const empty = !d.todo.open_flags.length && !d.todo.asks.length && !d.todo.pending_apaar.length;

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <section aria-labelledby="w-h" className="flex flex-col gap-1">
        <h2 id="w-h" className="font-semibold">{t("home.window")} ({d.cycle_year})</h2>
        {!w ? <p className="text-sm text-muted-foreground">{t("home.window.none")}</p> : (
          <>
            <p className="flex items-center gap-2 text-sm">
              <CalendarClock aria-hidden className="size-4" />
              <span className="font-medium">{t(`home.window.${w.state}`)}</span>
              {w.state === "open" && c && <span className="tabular-nums">- {t("home.window.closesIn")} {c.days}{t("unit.days")} {c.hours}{t("unit.hours")}</span>}
              {w.state === "closed" && c && <span className="tabular-nums">- {t("home.window.closedAgo")} {c.days}{t("unit.days")} {c.hours}{t("unit.hours")}</span>}
              {w.state === "not_open" && <span>- {t("home.window.opens")} {formatDateTime(w.opens_at)}</span>}
            </p>
            <p className="text-sm text-muted-foreground">{formatDateTime(w.opens_at)} to {formatDateTime(w.closes_at)}</p>
            <p className="text-sm">{t(w.submitted ? "home.window.submitted" : "home.window.notSubmitted")}</p>
          </>
        )}
      </section>

      <section aria-labelledby="c-h">
        <h2 id="c-h" className="mb-2 font-semibold">{t("home.counts")}</h2>
        <dl className="flex flex-wrap gap-x-8 gap-y-2">
          {([["home.accepted", d.records.accepted], ["home.flagged", d.records.flagged], ["home.pending", d.records.pending_apaar]] as const).map(([k, v]) => (
            <div key={k}><dt className="text-xs text-muted-foreground">{t(k)}</dt><dd className="t-figure text-primary">{v}</dd></div>
          ))}
        </dl>
      </section>

      <section aria-labelledby="t-h">
        <h2 id="t-h" className="mb-2 font-semibold">{t("home.todo")}</h2>
        {empty ? <p className="text-sm text-muted-foreground">{t("home.todo.empty")}</p> : (
          <ul className="flex flex-col gap-4">
            <Todo title={t("home.todo.asks")} items={d.todo.asks} href="/institution/flags" />
            <Todo title={t("home.todo.flags")} items={d.todo.open_flags} href="/institution/flags" />
            {d.todo.pending_apaar.length > 0 && (
              <li>
                <p className="font-medium">{t("home.todo.pending")} <span className="tabular-nums text-muted-foreground">({d.todo.pending_apaar.length})</span></p>
                <ul className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm">
                  {d.todo.pending_apaar.map((r) => (
                    <li key={r.record_id}><Link className="underline-offset-2 hover:underline" href={`/institution/records/${r.record_id}`}>{t("home.todo.row")} {r.row_number}</Link></li>
                  ))}
                </ul>
              </li>
            )}
          </ul>
        )}
      </section>
    </div>
  );
}
