"use client";
import Link from "next/link";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Evidence, RecordList, RuleChip, StateBadge, Timeline, Age } from "@/components/flag-parts";
import { NoteDialog } from "@/components/note-dialog";
import { PageHeader } from "@/components/page-header";
import { QueryError } from "@/components/query-error";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { allowedActions, type FlagAction } from "@/lib/review";
import type { FlagDetail } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";

export function FlagDetailView({ id, backHref }: { id: string; backHref: string }) {
  const { t, user } = useAuth();
  const qc = useQueryClient();
  const path = `/flags/${id}`;
  // This read is audited (FLAG.VIEWED): fetch once; refetch only after an action or a 409.
  const q = useApiQuery<FlagDetail>(path, { refetchOnWindowFocus: false, staleTime: Infinity });
  const [action, setAction] = useState<FlagAction | null>(null);
  const f = q.data;

  const run = useMutation({
    mutationFn: (v: { action: FlagAction; note: string }) =>
      api.post(`${path}/${v.action}`, { note: v.note, lock_version: f?.lock_version }),
    onSuccess: () => {
      setAction(null);
      toast.success(t("flag.action.done"));
      qc.invalidateQueries({ queryKey: ["api", path] });
      qc.invalidateQueries({ queryKey: ["api", "/flags"] });
    },
    onError: (e) => {
      setAction(null);
      if (e instanceof ApiError && e.status === 409) {
        toast.error(t("flag.stale"));
        q.refetch();
      } else if (e instanceof ApiError && e.status === 403) toast.error(t("error.forbidden"));
      else toast.error(e instanceof ApiError ? e.message : t("error.generic"));
    },
  });

  const actions = f ? allowedActions(f.state, user?.role, f.rule_code) : [];
  const isInst = user?.role?.startsWith("INSTITUTION");

  return (
    <>
      <PageHeader title={t("flag.detail")} actions={<Link className="text-sm underline" href={backHref}>{t("flag.back")}</Link>} />
      {q.isPending && <Skeleton className="h-48 w-full max-w-3xl" />}
      {q.isError && <QueryError error={q.error} onRetry={() => q.refetch()} />}
      {f && (
        <div className="flex max-w-4xl flex-col gap-8">
          <section aria-labelledby="fh" className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-3">
              <RuleChip code={f.rule_code} />
              <StateBadge state={f.state} />
              <span className="text-sm text-muted-foreground">{f.institution_name} · <Age days={f.age_days} /></span>
            </div>
            <h2 id="fh" className="sr-only">{t("flag.reason")}</h2>
            <p className="text-base">{f.reason}</p>
            {f.state === "ask_institution" && isInst && <p className="text-sm font-medium text-status-alert">{t("inst.flags.asked")}</p>}
            {actions.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {actions.map((a) => (
                  <Button key={a} variant={a === "resolve" ? "default" : "outline"} onClick={() => setAction(a)}>
                    {t(`flag.action.${a}`)}
                  </Button>
                ))}
              </div>
            )}
            {!isInst && <p className="text-xs text-muted-foreground">{t("flag.advisory")}</p>}
          </section>
          <section aria-labelledby="eh" className="flex flex-col gap-3">
            <h2 id="eh" className="font-semibold">{t("flag.evidence")}</h2>
            <Evidence flag={f} />
            <p className="text-xs text-muted-foreground">
              {t("flag.ruleVersion")} <span className="font-mono">{f.rule_code} v{f.rule_version.version_no}</span>
            </p>
          </section>
          <section aria-labelledby="rh" className="flex flex-col gap-3">
            <h2 id="rh" className="font-semibold">{t("flag.records")}</h2>
            <RecordList records={f.records} />
          </section>
          <section aria-labelledby="hh" className="flex flex-col gap-3">
            <h2 id="hh" className="font-semibold">{isInst ? t("inst.flags.officerNotes") : t("flag.history")}</h2>
            <Timeline events={f.events} />
          </section>
        </div>
      )}
      {action && (
        <NoteDialog open t={t} title={`flag.action.${action}`} label="flag.note" confirmLabel={`flag.action.${action}`}
                    pending={run.isPending} onClose={() => setAction(null)}
                    onSubmit={(note) => run.mutate({ action, note })} />
      )}
    </>
  );
}
