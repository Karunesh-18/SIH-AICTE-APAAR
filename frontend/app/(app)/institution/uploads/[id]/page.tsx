"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { FlagCard } from "@/components/flag-list";
import { PageHeader } from "@/components/page-header";
import { QueryError } from "@/components/query-error";
import { ErrorState } from "@/components/states";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/auth";
import { pollInterval } from "@/lib/poll";
import { formatDateTime } from "@/lib/status";
import type { Upload } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";

function Figure({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="text-lg font-semibold tabular-nums">{value}</dd>
    </div>
  );
}

export default function Page() {
  const { id } = useParams<{ id: string }>();
  const { t } = useAuth();
  // refetchInterval is owned by the query, so polling stops on unmount and once DONE or REJECTED.
  const q = useApiQuery<Upload>(`/uploads/${id}`, { refetchInterval: (query) => pollInterval(query.state.data?.status) });
  const up = q.data;

  return (
    <>
      <PageHeader title={t("receipt.title")} description={up ? `${t("receipt.id")} ${up.id}` : undefined}
                  actions={<Link className="text-sm underline" href="/institution/upload">{t("receipt.another")}</Link>} />
      {q.isPending && <Skeleton className="h-24 w-full max-w-2xl" />}
      {q.isError && <QueryError error={q.error} onRetry={() => q.refetch()} />}
      {up && up.status === "REJECTED" && (
        <ErrorState message={`${t("receipt.rejected")} ${up.error ?? ""}`} />
      )}
      {up && up.status !== "REJECTED" && (
        <div className="flex max-w-3xl flex-col gap-6">
          {up.status !== "DONE" ? (
            <p role="status" className="flex items-center gap-2 text-sm">
              <Loader2 aria-hidden className="size-4 animate-spin" /> {t("receipt.processing")}
            </p>
          ) : (
            <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Figure label={t("receipt.rows")} value={up.row_count ?? 0} />
              <Figure label={t("receipt.accepted")} value={up.accepted_count} />
              <Figure label={t("receipt.flagged")} value={up.flagged_count} />
              <Figure label={t("receipt.flags")} value={up.flags.total} />
            </dl>
          )}
          <p className="text-sm text-muted-foreground">
            {t("receipt.received")} {formatDateTime(up.created_at)} - {up.format.toUpperCase()} - {up.cycle_year}
          </p>
          {up.status === "DONE" && (
            <section aria-labelledby="flags-h" className="flex flex-col gap-3">
              <h2 id="flags-h" className="font-semibold">{t("receipt.flagsHeading")}</h2>
              <p className="text-sm text-muted-foreground">{t("receipt.advisory")}</p>
              {up.flag_items && up.flag_items.length > 0 ? (
                <ul className="flex flex-col gap-3">{up.flag_items.map((f) => <FlagCard key={f.id} flag={f} />)}</ul>
              ) : (
                <p className="text-sm">{t("receipt.noFlags")}</p>
              )}
            </section>
          )}
        </div>
      )}
    </>
  );
}
