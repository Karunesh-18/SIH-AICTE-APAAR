"use client";
import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { QueryError } from "@/components/query-error";
import { EmptyState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDateTime } from "@/lib/status";
import type { Notification } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";

export default function Page() {
  const { t, user } = useAuth();
  const qc = useQueryClient();
  const q = useApiQuery<Notification[]>("/notifications");
  const read = useMutation({
    mutationFn: (id: string) => api.post(`/notifications/${id}/read`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["api", "/notifications"] });
      qc.invalidateQueries({ queryKey: ["api", "/notifications/unread-count"] });
    },
    onError: () => toast.error(t("error.generic")),
  });
  const flagHref = (id: string) => `${user?.role.startsWith("INSTITUTION") ? "/institution/flags" : "/review"}/${id}`;

  return (
    <>
      <PageHeader title={t("notif.title")} />
      {q.isPending && <Skeleton className="h-32 w-full max-w-2xl" />}
      {q.isError && <QueryError error={q.error} onRetry={() => q.refetch()} />}
      {q.data?.length === 0 && <EmptyState title={t("notif.empty")} />}
      <ul className="flex max-w-3xl flex-col gap-2">
        {q.data?.map((n) => (
          <li key={n.id} className={`flex flex-wrap items-start justify-between gap-3 rounded-md border border-border p-3 text-sm ${n.read_at ? "text-muted-foreground" : ""}`}>
            <div>
              <p className={n.read_at ? "" : "font-medium"}>{n.subject}</p>
              <p className="mt-0.5">{n.body}</p>
              <p className="mt-1 text-xs tabular-nums">{formatDateTime(n.created_at)}</p>
            </div>
            <div className="flex items-center gap-2">
              {n.related_type === "validation_flag" && n.related_id && (
                <Link className="underline" href={flagHref(n.related_id)}>{t("notif.open")}</Link>
              )}
              {n.read_at ? <span className="text-xs">{t("notif.read")}</span> : (
                <Button size="sm" variant="outline" disabled={read.isPending} onClick={() => read.mutate(n.id)}>{t("notif.markRead")}</Button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </>
  );
}
