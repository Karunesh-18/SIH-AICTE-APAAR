"use client";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { QueryError } from "@/components/query-error";
import { RoleGuard } from "@/components/role-guard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDateTime } from "@/lib/status";
import type { ClockState } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";

function Clock() {
  const { t } = useAuth();
  const qc = useQueryClient();
  const q = useApiQuery<ClockState>("/admin/clock");
  const [days, setDays] = useState("1");
  const [busy, setBusy] = useState(false);
  const n = Number(days);
  const ok = Number.isFinite(n) && n !== 0;

  async function post(body: { advance_days: number } | { reset: true }) {
    setBusy(true);
    try {
      qc.setQueryData(["api", "/admin/clock"], await api.post<ClockState>("/admin/clock", body));
      toast.success(t("clock.updated"));
    } catch {
      toast.error(t("error.action"));
    }
    setBusy(false);
  }

  return (
    <>
      <PageHeader title={t("clock.title")} description={t("clock.intro")} />
      {q.isPending && <Skeleton className="h-20 w-full max-w-md" />}
      {q.isError && <QueryError error={q.error} onRetry={() => q.refetch()} />}
      {q.data && (
        <div className="flex max-w-xl flex-col gap-6">
          <dl aria-live="polite" className="flex flex-wrap gap-x-10 gap-y-2">
            <div><dt className="text-xs text-muted-foreground">{t("clock.now")}</dt><dd className="text-lg font-semibold tabular-nums">{formatDateTime(q.data.now)}</dd></div>
            <div><dt className="text-xs text-muted-foreground">{t("clock.offset")}</dt><dd className="text-lg font-semibold tabular-nums">{q.data.offset_days}</dd></div>
          </dl>
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => { e.preventDefault(); if (ok) post({ advance_days: n }); }}>
            <div className="flex flex-col gap-1">
              <Label htmlFor="c-days">{t("clock.advance")}</Label>
              <Input id="c-days" type="number" step="any" className="w-28" value={days} onChange={(e) => setDays(e.target.value)} />
            </div>
            <Button type="submit" disabled={!ok || busy}>{t("clock.advanceBtn")}</Button>
            <Button type="button" variant="outline" disabled={busy || q.data.offset_days === 0} onClick={() => post({ reset: true })}>{t("clock.reset")}</Button>
          </form>
          {!ok && <p role="status" className="text-sm text-muted-foreground">{t("clock.invalid")}</p>}
        </div>
      )}
    </>
  );
}

export default function Page() {
  return (
    <RoleGuard roles={["AICTE_ADMIN"]}>
      <Clock />
    </RoleGuard>
  );
}
