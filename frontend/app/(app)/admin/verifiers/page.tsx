"use client";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { NoteDialog } from "@/components/note-dialog";
import { PageHeader } from "@/components/page-header";
import { QueryError } from "@/components/query-error";
import { RoleGuard } from "@/components/role-guard";
import { EmptyState } from "@/components/states";
import { ToneBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDateTime, type StatusMeta } from "@/lib/status";
import type { VerifierReg } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";

const PATH = "/admin/verifiers";
const META: Record<string, StatusMeta> = {
  PENDING: { labelKey: "vreg.status.PENDING", icon: "clock", tone: "alert" },
  APPROVED: { labelKey: "vreg.status.APPROVED", icon: "check", tone: "clear" },
  REJECTED: { labelKey: "vreg.status.REJECTED", icon: "x", tone: "excess" },
};

function Card({ v, onDecide }: { v: VerifierReg; onDecide?: (a: "approve" | "reject") => void }) {
  const { t } = useAuth();
  return (
    <li className="flex flex-col gap-2 rounded-md border border-border p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-medium">{v.org_name} <span className="font-normal text-muted-foreground">({t(`orgType.${v.org_type}`)})</span></p>
        <ToneBadge meta={META[v.status]} label={t(META[v.status].labelKey)} />
      </div>
      <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-sm">
        <dt className="text-muted-foreground">{t("vreg.contact")}</dt><dd>{v.contact} ({v.email})</dd>
        <dt className="text-muted-foreground">{t("vreg.requested")}</dt><dd>{v.requested_purposes.map((p) => t(`purpose.${p}`)).join(", ")}</dd>
        <dt className="text-muted-foreground">{t("vreg.registered")}</dt><dd>{formatDateTime(v.created_at)}</dd>
        {v.decision_note && (<><dt className="text-muted-foreground">{t("vreg.decisionNote")}</dt><dd>{v.decision_note}</dd></>)}
      </dl>
      {onDecide && (
        <div className="flex gap-2">
          <Button size="sm" onClick={() => onDecide("approve")}>{t("vreg.approve")}</Button>
          <Button size="sm" variant="outline" onClick={() => onDecide("reject")}>{t("vreg.reject")}</Button>
        </div>
      )}
    </li>
  );
}

function Verifiers() {
  const { t } = useAuth();
  const qc = useQueryClient();
  const q = useApiQuery<{ items: VerifierReg[] }>(PATH);
  const [pending, setPending] = useState<{ v: VerifierReg; action: "approve" | "reject" } | null>(null);
  const [busy, setBusy] = useState(false);
  const items = q.data?.items ?? [];
  const waiting = items.filter((v) => v.status === "PENDING");
  const decided = items.filter((v) => v.status !== "PENDING");

  async function decide(note: string) {
    if (!pending) return;
    setBusy(true);
    try {
      await api.post(`${PATH}/${pending.v.id}/${pending.action}`, { note });
      toast.success(t("vreg.decided"));
    } catch (err) {
      toast.error(err instanceof ApiError && err.status === 409 ? t("vreg.conflict") : t("error.action"));
    }
    setPending(null);
    setBusy(false);
    qc.invalidateQueries({ queryKey: ["api", PATH] });
  }

  return (
    <>
      <PageHeader title={t("vreg.title")} description={t("vreg.intro")} />
      {q.isPending && <Skeleton className="h-32 w-full max-w-2xl" />}
      {q.isError && <QueryError error={q.error} onRetry={() => q.refetch()} />}
      {q.data && (
        <div className="flex max-w-2xl flex-col gap-8">
          <section aria-labelledby="vp" className="flex flex-col gap-3">
            <h2 id="vp" className="text-base font-semibold">{t("vreg.pending")} ({waiting.length})</h2>
            {waiting.length === 0 ? <EmptyState title={t("vreg.pendingEmpty")} /> : (
              <ul className="flex flex-col gap-3">{waiting.map((v) => <Card key={v.id} v={v} onDecide={(action) => setPending({ v, action })} />)}</ul>
            )}
          </section>
          <section aria-labelledby="vh" className="flex flex-col gap-3">
            <h2 id="vh" className="text-base font-semibold">{t("vreg.history")}</h2>
            {decided.length === 0 ? <EmptyState title={t("vreg.historyEmpty")} /> : (
              <ul className="flex flex-col gap-3">{decided.map((v) => <Card key={v.id} v={v} />)}</ul>
            )}
          </section>
        </div>
      )}
      <NoteDialog open={!!pending} title={pending?.action === "approve" ? "vreg.approveTitle" : "vreg.rejectTitle"} label="vreg.note"
        description={pending?.v.org_name} confirmLabel={pending?.action === "approve" ? "vreg.approve" : "vreg.reject"}
        destructive={pending?.action === "reject"} pending={busy} t={t} onSubmit={decide} onClose={() => setPending(null)} />
    </>
  );
}

export default function Page() {
  return (
    <RoleGuard roles={["AICTE_ADMIN"]}>
      <Verifiers />
    </RoleGuard>
  );
}
