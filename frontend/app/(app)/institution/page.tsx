"use client";
import Link from "next/link";
import { RoleGuard } from "@/components/role-guard";
import { PageHeader } from "@/components/page-header";
import { QueryError } from "@/components/query-error";
import { EmptyState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/auth";
import { pollInterval } from "@/lib/poll";
import { formatDateTime } from "@/lib/status";
import type { Page as Paged, Upload } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";
import { InstitutionStatus } from "@/components/institution-status";

function Home() {
  const { t } = useAuth();
  const q = useApiQuery<Paged<Upload>>("/uploads?limit=1", {
    refetchInterval: (query) => pollInterval(query.state.data?.items[0]?.status ?? "DONE"),
  });
  const latest = q.data?.items[0];
  const upload = <Button render={<Link href="/institution/upload" />}>{t("home.upload")}</Button>;

  return (
    <>
      <PageHeader title={t("home.title")} actions={latest ? upload : undefined} />
      <InstitutionStatus />
      {q.isPending && <Skeleton className="h-20 w-full max-w-xl" />}
      {q.isError && <QueryError error={q.error} onRetry={() => q.refetch()} />}
      {q.data && !latest && (
        <EmptyState title={t("home.none")} hint={t("home.noneHint")} action={upload} />
      )}
      {latest && (
        <section aria-labelledby="latest-h" className="mt-8 flex max-w-xl flex-col gap-3">
          <h2 id="latest-h" className="font-semibold">{t("home.latest")}</h2>
          <p className="text-sm text-muted-foreground">
            {formatDateTime(latest.created_at)} - {latest.cycle_year} - {t(`upload.status.${latest.status}`)}
          </p>
          {latest.status === "DONE" && (
            <p className="text-sm tabular-nums">
              {t("receipt.rows")}: {latest.row_count} - {t("receipt.accepted")}: {latest.accepted_count} - {t("receipt.flagged")}: {latest.flagged_count}
            </p>
          )}
          <Link className="text-sm underline" href={`/institution/uploads/${latest.id}`}>{t("home.openReceipt")}</Link>
        </section>
      )}
    </>
  );
}

export default function Page() {
  return (
    <RoleGuard roles={["INSTITUTION_ADMIN", "INSTITUTION_STAFF"]}>
      <Home />
    </RoleGuard>
  );
}
