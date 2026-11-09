"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Copy, TriangleAlert } from "lucide-react";
import { toast } from "sonner";
import { DataTable, type Col } from "@/components/data-table";
import { PageHeader } from "@/components/page-header";
import { RoleGuard } from "@/components/role-guard";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDateTime } from "@/lib/status";
import type { ApiKey, NewApiKey } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";

function Keys() {
  const { t, user } = useAuth();
  const qc = useQueryClient();
  const inst = user?.institution_id;
  const path = inst ? `/institutions/${inst}/api-keys` : null;
  const q = useApiQuery<ApiKey[]>(path);
  const [name, setName] = useState("");
  const [shown, setShown] = useState<NewApiKey | null>(null);
  const [revoking, setRevoking] = useState<ApiKey | null>(null);
  const refresh = () => qc.invalidateQueries({ queryKey: ["api", path] });
  const fail = (e: unknown) => toast.error(e instanceof ApiError ? e.message : t("error.generic"));

  const create = useMutation({
    mutationFn: () => api.post<NewApiKey>(path as string, { name: name.trim() || "key" }),
    onSuccess: (k) => { setShown(k); setName(""); refresh(); },
    onError: fail,
  });
  const revoke = useMutation({
    mutationFn: (k: ApiKey) => api.del(`${path}/${k.id}`),
    onSuccess: () => { setRevoking(null); refresh(); toast.success(t("keys.revoked")); },
    onError: fail,
  });

  const columns: Col<ApiKey>[] = [
    { accessorKey: "name", header: t("keys.name") },
    { accessorKey: "prefix", header: t("keys.prefix"), cell: (c) => <span className="font-mono">{c.getValue() as string}...</span> },
    { accessorKey: "created_at", header: t("keys.created"), cell: (c) => formatDateTime(c.getValue() as string) },
    { accessorKey: "last_used_at", header: t("keys.lastUsed"), cell: (c) => (c.getValue() ? formatDateTime(c.getValue() as string) : t("keys.never")) },
    { id: "state", header: t("record.status"), enableSorting: false,
      cell: (c) => (c.row.original.revoked_at ? t("keys.revokedState") : t("keys.active")) },
    { id: "act", header: "", enableSorting: false,
      cell: (c) => c.row.original.revoked_at ? null : (
        <Button variant="outline" size="sm" onClick={() => setRevoking(c.row.original)}>{t("keys.revoke")}</Button>
      ) },
  ];

  return (
    <>
      <PageHeader title={t("nav.apiKeys")} description={t("keys.intro")} />
      <form className="mb-6 flex max-w-md items-end gap-2" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}>
        <div className="flex flex-1 flex-col gap-1.5">
          <Label htmlFor="kn">{t("keys.nameLabel")}</Label>
          <Input id="kn" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <Button type="submit" disabled={create.isPending || !inst}>{t("keys.create")}</Button>
      </form>
      <DataTable columns={columns} caption={t("nav.apiKeys")} data={q.data ?? []} loading={q.isPending && !!inst}
                 error={q.isError ? (q.error.status === 403 ? t("error.forbidden") : t("error.generic")) : null}
                 onRetry={() => q.refetch()}
                 labels={{ empty: t("keys.empty"), error: t("error.generic"), retry: t("state.retry"), prev: t("table.prev"), next: t("table.next") }} />

      <Dialog open={!!shown} onOpenChange={(o) => { if (!o) setShown(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("keys.newTitle")}</DialogTitle>
            <DialogDescription className="flex items-start gap-2 text-status-alert">
              <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0" /> {t("keys.once")}
            </DialogDescription>
          </DialogHeader>
          <code className="block break-all rounded-md bg-muted p-3 font-mono text-sm">{shown?.key}</code>
          <DialogFooter>
            <Button variant="outline" onClick={() => navigator.clipboard.writeText(shown?.key ?? "").then(
              () => toast.success(t("keys.copied")), () => toast.error(t("error.generic")))}>
              <Copy data-icon="inline-start" /> {t("keys.copy")}
            </Button>
            <Button onClick={() => setShown(null)}>{t("keys.done")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!revoking} onOpenChange={(o) => { if (!o) setRevoking(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("keys.revokeTitle")}</DialogTitle>
            <DialogDescription>{t("keys.revokeBody")} {revoking?.name}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRevoking(null)}>{t("dialog.cancel")}</Button>
            <Button variant="destructive" disabled={revoke.isPending} onClick={() => revoking && revoke.mutate(revoking)}>{t("keys.revoke")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default function Page() {
  return (
    <RoleGuard roles={["INSTITUTION_ADMIN"]}>
      <Keys />
    </RoleGuard>
  );
}
