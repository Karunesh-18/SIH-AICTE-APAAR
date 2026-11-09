"use client";
import Link from "next/link";
import { useState } from "react";
import { DataTable, type Col } from "@/components/data-table";
import { FilterSelect } from "@/components/filter-select";
import { IntakeChart, RulesChart } from "@/components/charts";
import { PageHeader } from "@/components/page-header";
import { QueryError } from "@/components/query-error";
import { InstitutionStateBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/auth";
import { fmtInt, fmtPct } from "@/lib/dash";
import { formatDateTime } from "@/lib/status";
import type { AicteDashboard, DashInstitution, FlagsTrend, RegionRow } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";

const TYPES = ["ENGINEERING", "MANAGEMENT", "PHARMACY", "OTHER"];
const STATES = ["Clear", "Alert", "Excess"];

export function AicteDashboardView() {
  const { t } = useAuth();
  const [region, setRegion] = useState("");
  const [type, setType] = useState("");
  const [state, setState] = useState("");
  const regions = useApiQuery<RegionRow[]>("/regions");

  const qs = (o: Record<string, string>) => new URLSearchParams(Object.entries(o).filter(([, v]) => v)).toString();
  const dash = useApiQuery<AicteDashboard>(`/dashboards/aicte?${qs({ region, type, state })}`);
  const trend = useApiQuery<FlagsTrend>(`/dashboards/flags-trend?${qs({ region, type })}`);
  const active = region || type || state;
  const tl = dash.data?.tiles;
  const figures = tl && [
    ["dash.tile.institutions", fmtInt(tl.institutions)], ["dash.tile.records", fmtInt(tl.records)],
    ["dash.tile.open_flags", fmtInt(tl.open_flags)], ["dash.tile.excess", fmtInt(tl.excess)],
    ["dash.tile.alert", fmtInt(tl.alert)], ["dash.tile.pending", fmtPct(tl.pending_apaar_share)],
  ];

  const columns: Col<DashInstitution>[] = [
    { accessorKey: "name", header: t("col.institution"),
      cell: (c) => <Link className="font-medium underline-offset-2 hover:underline" href={`/aicte/institutions/${c.row.original.id}`}>{c.getValue() as string}</Link> },
    { accessorKey: "state", header: t("col.state"), cell: (c) => <InstitutionStateBadge state={c.getValue() as string} label={t(`state.${c.getValue()}`)} /> },
    { accessorKey: "region", header: t("col.region") },
    { accessorKey: "type", header: t("col.type"), cell: (c) => t(`inst.type.${c.getValue()}`) },
    { accessorKey: "enrolled", header: t("col.enrolment"),
      cell: (c) => <span className="tabular-nums">{fmtInt(c.row.original.enrolled)} / {fmtInt(c.row.original.allowed)}</span> },
    { accessorKey: "open_flags", header: t("col.flags"),
      cell: (c) => {
        const f = c.row.original.flags;
        const detail = Object.entries(f).map(([r, n]) => `${r}: ${n}`).join(", ");
        return <span title={detail} className="tabular-nums">{c.row.original.open_flags}{detail && <span className="text-muted-foreground"> ({detail})</span>}</span>;
      } },
    { accessorKey: "last_upload", header: t("col.lastUpload"), cell: (c) => formatDateTime(c.getValue() as string | null) },
  ];

  return (
    <>
      <PageHeader title={t("dash.title")} description={dash.data ? `${t("dash.cycle")} ${dash.data.cycle_year}` : undefined} />
      {dash.isError ? <QueryError error={dash.error} onRetry={() => dash.refetch()} /> : (
        <>
          <section aria-label={t("dash.title")} className="mb-4">
            {figures ? (
              <dl className="flex flex-wrap gap-x-8 gap-y-3">
                {figures.map(([k, v]) => (
                  <div key={k}>
                    <dt className="text-xs text-muted-foreground">{t(k)}</dt>
                    <dd className="t-figure text-primary">{v}</dd>
                  </div>
                ))}
              </dl>
            ) : <Skeleton className="h-12 w-full max-w-2xl" />}
            <p className="mt-2 text-xs text-muted-foreground">{t("dash.tilesNote")}</p>
          </section>

          <form role="search" className="mb-4 flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FilterSelect id="d-region" label={t("filter.region")} value={region} onChange={setRegion} any={t("filter.allRegions")}
                          options={(regions.data ?? []).map((r) => ({ value: r.code, label: r.name }))} />
            <FilterSelect id="d-type" label={t("filter.type")} value={type} onChange={setType} any={t("filter.any")}
                          options={TYPES.map((v) => ({ value: v, label: t(`inst.type.${v}`) }))} />
            <FilterSelect id="d-state" label={t("filter.state")} value={state} onChange={setState} any={t("filter.any")}
                          options={STATES.map((v) => ({ value: v, label: t(`state.${v}`) }))} />
            {active && <Button type="button" variant="outline" size="sm" onClick={() => { setRegion(""); setType(""); setState(""); }}>{t("filter.clear")}</Button>}
          </form>

          <DataTable columns={columns} caption={t("dash.table")} data={dash.data?.institutions ?? []} loading={dash.isPending}
                     labels={{ empty: t("dash.empty"), error: t("error.generic"), retry: t("state.retry"), prev: t("table.prev"), next: t("table.next") }} />

          {dash.data && dash.data.institutions.length > 0 && (
            <div className="mt-6 grid gap-4 xl:grid-cols-2">
              <IntakeChart rows={dash.data.institutions} />
              {trend.isPending ? <Skeleton className="h-80 w-full" /> :
                trend.isError ? <QueryError error={trend.error} onRetry={() => trend.refetch()} /> :
                  <RulesChart rows={trend.data.rows} />}
            </div>
          )}
        </>
      )}
    </>
  );
}
