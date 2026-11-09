"use client";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { DataTable, type Col } from "@/components/data-table";
import { QueryError } from "@/components/query-error";
import { ToneBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fieldLabelKey, refusalKey } from "@/lib/consent";
import { formatDateTime, outcomeMeta } from "@/lib/status";
import type { VerificationRow } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";

const LIST = "/verifications?limit=100";
const fieldsText = (t: (k: string) => string, fs: string[]) => fs.map((f) => t(fieldLabelKey(f))).join(", ") || "-";

function Detail({ id, canRevoke, onClose, onChanged }: { id: string; canRevoke: boolean; onClose: () => void; onChanged: () => void }) {
  const { t } = useAuth();
  const q = useApiQuery<VerificationRow>(`/verifications/${id}`, { staleTime: 0 });
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const r = q.data;

  async function revoke() {
    setBusy(true);
    try {
      await api.post(`/verifications/${id}/revoke`);
      toast.success(t("vr.revokeDone"));
      setConfirm(false);
      await q.refetch();
      onChanged();
    } catch {
      toast.error(t("error.action"));
    }
    setBusy(false);
  }

  const row = (label: string, value: string) => (
    <div className="contents"><dt className="text-muted-foreground">{label}</dt><dd>{value}</dd></div>
  );
  return (
    <>
      <Dialog open onOpenChange={(o) => { if (!o) onClose(); }}>
        <DialogContent>
          <DialogHeader><DialogTitle>{t("ver.detail")}</DialogTitle></DialogHeader>
          {q.isPending && <Skeleton className="h-32 w-full" />}
          {q.isError && <QueryError error={q.error} onRetry={() => q.refetch()} />}
          {r && (
            <div className="flex flex-col gap-3">
              <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-sm">
                {row(t("col.when"), formatDateTime(r.created_at))}
                {r.verifier && row(t("col.verifier"), r.verifier)}
                {row(t("col.apaar"), r.apaar_id)}
                {row(t("col.purpose"), t(`purpose.${r.purpose}`))}
                {row(t("ver.requested"), fieldsText(t, r.fields_requested))}
                {r.refusal_reason && row(t("col.reason"), t(refusalKey(r.refusal_reason)))}
                {r.refusal_detail && row(t("ver.detailFields"), fieldsText(t, r.refusal_detail))}
                {r.issued_at && row(t("ver.issued"), formatDateTime(r.issued_at))}
                {r.expires_at && row(t("col.expires"), formatDateTime(r.expires_at))}
                {r.revoked_at && row(t("ver.revokedAt"), formatDateTime(r.revoked_at))}
                {r.consent_id && row(t("ver.consentId"), r.consent_id)}
              </dl>
              <div><ToneBadge meta={outcomeMeta(r.outcome, r.revoked_at)} label={t(outcomeMeta(r.outcome, r.revoked_at).labelKey)} /></div>
              {canRevoke && r.outcome === "GRANTED" && !r.revoked_at && (
                <Button variant="destructive" size="sm" className="w-fit" onClick={() => setConfirm(true)}>{t("ver.revokeBtn")}</Button>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
      <ConfirmDialog open={confirm} title={t("vr.revokeTitle")} body={t("vr.revokeBody")} confirmLabel={t("vr.revoke")}
        cancelLabel={t("dialog.cancel")} pending={busy} onConfirm={revoke} onClose={() => setConfirm(false)} />
    </>
  );
}

/** Scoped by the server: AICTE admin sees all, an officer their regions, an institution its own students. */
export function VerificationList() {
  const { t, user } = useAuth();
  const qc = useQueryClient();
  const q = useApiQuery<{ items: VerificationRow[] }>(LIST);
  const [open, setOpen] = useState<string | null>(null);

  const columns: Col<VerificationRow>[] = [
    { accessorKey: "created_at", header: t("col.when"), cell: (c) => formatDateTime(c.getValue() as string) },
    { accessorKey: "verifier", header: t("col.verifier") },
    { accessorKey: "apaar_id", header: t("col.apaar"), cell: (c) => <span className="font-mono">{c.getValue() as string}</span> },
    { accessorKey: "purpose", header: t("col.purpose"), cell: (c) => t(`purpose.${c.getValue() as string}`) },
    { accessorKey: "outcome", header: t("col.outcome"), cell: (c) => {
      const m = outcomeMeta(c.row.original.outcome, c.row.original.revoked_at);
      return <ToneBadge meta={m} label={t(m.labelKey)} />;
    } },
    { accessorKey: "refusal_reason", header: t("col.reason"), enableSorting: false,
      cell: (c) => (c.getValue() ? t(refusalKey(c.getValue() as string)) : "-") },
    { id: "open", header: t("col.actions"), enableSorting: false, cell: (c) => (
      <Button variant="outline" size="sm" onClick={() => setOpen(c.row.original.id)}>{t("ver.detail")}</Button>
    ) },
  ];

  return (
    <>
      <DataTable columns={columns} data={q.data?.items ?? []} loading={q.isPending} onRetry={() => q.refetch()}
        error={q.isError ? t(q.error.status === 403 ? "error.forbidden" : "error.generic") : null}
        labels={{ empty: t("ver.empty"), error: t("error.generic"), retry: t("state.retry"), prev: t("table.prev"), next: t("table.next") }} />
      {open && <Detail id={open} canRevoke={user?.role === "AICTE_ADMIN"} onClose={() => setOpen(null)}
        onChanged={() => qc.invalidateQueries({ queryKey: ["api", LIST] })} />}
    </>
  );
}
