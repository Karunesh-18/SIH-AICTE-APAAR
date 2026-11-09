"use client";
import Link from "next/link";
import { DataTable, type Col } from "@/components/data-table";
import { PageHeader } from "@/components/page-header";
import { RoleGuard } from "@/components/role-guard";
import { useAuth } from "@/lib/auth";
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
  return (
    <>
      <PageHeader title={t("nav.rules")} description={t("rules.intro")} />
      <DataTable columns={columns} caption={t("nav.rules")} data={q.data ?? []} loading={q.isPending}
                 error={q.isError ? t(q.error.status === 403 ? "error.forbidden" : "error.generic") : null}
                 onRetry={() => q.refetch()}
                 labels={{ empty: t("rules.empty"), error: t("error.generic"), retry: t("state.retry"), prev: t("table.prev"), next: t("table.next") }} />
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
