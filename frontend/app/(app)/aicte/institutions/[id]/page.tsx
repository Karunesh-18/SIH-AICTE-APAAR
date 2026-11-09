"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { IntakeChart } from "@/components/charts";
import { DataTable, type Col } from "@/components/data-table";
import { Age, RuleChip, StateBadge } from "@/components/flag-parts";
import { PageHeader } from "@/components/page-header";
import { QueryError } from "@/components/query-error";
import { RoleGuard } from "@/components/role-guard";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/auth";
import { formatDateTime } from "@/lib/status";
import type { FlagRow, InstitutionRow, Page, ProgrammeRow, Upload } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";

function Detail({ id }: { id: string }) {
  const { t } = useAuth();
  const inst = useApiQuery<InstitutionRow>(`/institutions/${id}`);
  const prog = useApiQuery<{ rows: ProgrammeRow[] }>("/dashboards/intake-use");
  const flags = useApiQuery<Page<FlagRow>>(`/flags?institution=${id}&limit=50`);
  const ups = useApiQuery<Page<Upload>>("/uploads?limit=200");
  const mine = (prog.data?.rows ?? []).filter((r) => r.institution_id === id);
  const uploads = (ups.data?.items ?? []).filter((u) => u.institution_id === id);
  const labels = { error: t("error.generic"), retry: t("state.retry"), prev: t("table.prev"), next: t("table.next") };

  const progCols: Col<ProgrammeRow>[] = [
    { accessorKey: "programme", header: t("col.programme") },
    { accessorKey: "approved_intake", header: t("instd.approved") },
    { id: "super", header: t("instd.supernumerary"), accessorFn: (r) => r.allowed - r.approved_intake },
    { accessorKey: "allowed", header: t("chart.allowed") },
    { accessorKey: "enrolled", header: t("instd.actual") },
  ];
  const flagCols: Col<FlagRow>[] = [
    { accessorKey: "rule_code", header: t("col.rule"), cell: (c) => <RuleChip code={c.getValue() as string} /> },
    { accessorKey: "state", header: t("col.state"), cell: (c) => <StateBadge state={c.getValue() as string} /> },
    { accessorKey: "age_days", header: t("col.age"), cell: (c) => <Age days={c.getValue() as number} /> },
    { accessorKey: "reason", header: t("col.reason"), enableSorting: false,
      cell: (c) => <Link className="line-clamp-2 max-w-md underline-offset-2 hover:underline" href={`/review/${c.row.original.id}`}>{c.getValue() as string}</Link> },
  ];
  const upCols: Col<Upload>[] = [
    { accessorKey: "created_at", header: t("col.uploaded"), cell: (c) => formatDateTime(c.getValue() as string) },
    { accessorKey: "cycle_year", header: t("dash.cycle") },
    { accessorKey: "status", header: t("col.status"), cell: (c) => t(`upload.status.${c.getValue()}`) },
    { accessorKey: "row_count", header: t("col.rows") },
    { accessorKey: "accepted_count", header: t("col.accepted") },
    { accessorKey: "flagged_count", header: t("col.flagged") },
  ];

  return (
    <>
      <PageHeader title={inst.data?.name ?? t("instd.title")}
                  actions={<Link className="text-sm underline" href="/aicte">{t("instd.back")}</Link>} />
      {inst.isError && <QueryError error={inst.error} onRetry={() => inst.refetch()} />}
      {!inst.isError && (
        <div className="flex flex-col gap-8">
          <section aria-labelledby="p-h" className="flex flex-col gap-3">
            <h2 id="p-h" className="font-semibold">{t("instd.programmes")}</h2>
            <p className="text-sm text-muted-foreground">{t("instd.programmesNote")}</p>
            {prog.isError ? <QueryError error={prog.error} onRetry={() => prog.refetch()} /> : prog.isPending ? <Skeleton className="h-40 w-full" /> : (
              <>
                {mine.length > 0 && <IntakeChart rows={mine.map((r) => ({ id: r.programme, name: r.programme, enrolled: r.enrolled, allowed: r.allowed }))} />}
                <DataTable columns={progCols} data={mine} labels={{ ...labels, empty: t("chart.empty") }} />
              </>
            )}
          </section>
          <section aria-labelledby="f-h" className="flex flex-col gap-3">
            <h2 id="f-h" className="font-semibold">{t("instd.flags")}</h2>
            <DataTable columns={flagCols} data={flags.data?.items ?? []} loading={flags.isPending}
                       error={flags.isError ? t("error.generic") : null} onRetry={() => flags.refetch()}
                       labels={{ ...labels, empty: t("instd.flagsEmpty") }} />
          </section>
          <section aria-labelledby="u-h" className="flex flex-col gap-3">
            <h2 id="u-h" className="font-semibold">{t("instd.uploads")}</h2>
            <DataTable columns={upCols} data={uploads} loading={ups.isPending}
                       error={ups.isError ? t("error.generic") : null} onRetry={() => ups.refetch()}
                       labels={{ ...labels, empty: t("instd.uploadsEmpty") }} />
          </section>
        </div>
      )}
    </>
  );
}

export default function Page() {
  const { id } = useParams<{ id: string }>();
  return (
    <RoleGuard roles={["AICTE_ADMIN", "AICTE_OFFICER"]}>
      <Detail id={id} />
    </RoleGuard>
  );
}
