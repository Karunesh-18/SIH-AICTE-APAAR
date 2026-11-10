"use client";
import Link from "next/link";
import { DataTable, type Col } from "@/components/data-table";
import { PageHeader } from "@/components/page-header";
import { RoleGuard } from "@/components/role-guard";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth";
import { dash, healthShare, oftenDismissed, type RuleHealthRow } from "@/lib/rules";
import type { RuleSummary } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";

function Rules() {
  const { t } = useAuth();
  const q = useApiQuery<RuleSummary[]>("/admin/rules");
  const columns: Col<RuleSummary>[] = [
    { accessorKey: "code", header: t("rules.code"),
      cell: (c) => <Link className="font-mono underline" href={`/admin/rules/${c.getValue() as string}`}>{c.getValue() as string}</Link> },
    { accessorKey: "title", header: t("rules.title") },
    { id: "version", header: t("rules.version"), accessorFn: (r) => r.active?.version_no ?? 0,
      cell: (c) => `v${c.getValue() as number}` },
    { id: "enabled", header: t("rules.enabled"), accessorFn: (r) => (r.active?.enabled ? 1 : 0),
      cell: (c) => (c.getValue() ? t("rules.on") : t("rules.off")) },
    { id: "params", header: t("rules.params"), enableSorting: false,
      cell: (c) => <code className="font-mono text-xs">{JSON.stringify(c.row.original.active?.params ?? {})}</code> },
  ];
  const hq = useApiQuery<RuleHealthRow[]>("/admin/rules/health");
  const titles = new Map((q.data ?? []).map((r) => [r.code, r.title]));
  const num = (key: keyof RuleHealthRow, h: string): Col<RuleHealthRow> => ({
    accessorKey: key, header: t(h), cell: (c) => dash(c.getValue() as number | null) });
  const round1 = (v: number | null) => dash(v === null ? null : Math.round(v * 10) / 10);
  const healthCols: Col<RuleHealthRow>[] = [
    { accessorKey: "code", header: t("rules.code"),
      cell: (c) => <span><span className="font-mono">{c.row.original.code}</span> {titles.get(c.row.original.code)}</span> },
    num("raised", "rh.raised"), num("open", "rh.open"), num("resolved", "rh.resolved"), num("dismissed", "rh.dismissed"),
    { accessorKey: "dismissed_share", header: t("rh.share"),
      cell: (c) => <>{healthShare(c.row.original.dismissed_share)}{" "}
        {oftenDismissed(c.row.original) && <Badge variant="outline">{t("rh.often")}</Badge>}</> },
    { accessorKey: "median_days_to_close", header: t("rh.median"), cell: (c) => round1(c.row.original.median_days_to_close) },
    { accessorKey: "oldest_open_days", header: t("rh.oldest"), cell: (c) => round1(c.row.original.oldest_open_days) },
  ];
  return (
    <>
      <PageHeader title={t("nav.rules")} description={t("rules.intro")} />
      <DataTable columns={columns} caption={t("nav.rules")} data={q.data ?? []} loading={q.isPending}
                 error={q.isError ? t(q.error.status === 403 ? "error.forbidden" : "error.generic") : null}
                 onRetry={() => q.refetch()}
                 labels={{ empty: t("rules.empty"), error: t("error.generic"), retry: t("state.retry"), prev: t("table.prev"), next: t("table.next") }} />
      <h2 className="mt-8 mb-2 text-lg font-semibold">{t("rh.title")}</h2>
      <DataTable columns={healthCols} caption={t("rh.title")} data={hq.data ?? []} loading={hq.isPending}
                 error={hq.isError ? t("error.generic") : null} onRetry={() => hq.refetch()}
                 labels={{ empty: t("rh.empty"), error: t("error.generic"), retry: t("state.retry"), prev: t("table.prev"), next: t("table.next") }} />
      <p className="mt-2 text-sm text-muted-foreground">{t("rh.note")}</p>
    </>
  );
}

export default function Page() {
  return (
    <RoleGuard roles={["AICTE_ADMIN"]}>
      <Rules />
    </RoleGuard>
  );
}
