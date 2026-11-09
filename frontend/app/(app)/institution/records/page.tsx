"use client";
import Link from "next/link";
import { useState } from "react";
import { DataTable, type Col } from "@/components/data-table";
import { Masked } from "@/components/masked";
import { PageHeader } from "@/components/page-header";
import { RoleGuard } from "@/components/role-guard";
import { StatusBadge } from "@/components/status-badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAuth } from "@/lib/auth";
import type { Page as Paged, RecordRow } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";

const LIMIT = 25;
const STATUSES = ["all", "valid", "flagged", "pending_apaar", "withdrawn"] as const;

function Records() {
  const { t, user } = useAuth();
  const [status, setStatus] = useState<string>("all");
  const [offset, setOffset] = useState(0);
  const id = user?.institution_id;
  const qs = `limit=${LIMIT}&offset=${offset}` + (status === "all" ? "" : `&status=${status}`);
  const q = useApiQuery<Paged<RecordRow>>(id ? `/institutions/${id}/records?${qs}` : null);
  const m = t("record.masked");

  const columns: Col<RecordRow>[] = [
    { accessorKey: "row_number", header: t("record.row") },
    { accessorKey: "apaar_id", header: t("record.apaar"), cell: (c) => <Masked value={c.getValue() as string | null} label={m} /> },
    { accessorKey: "name", header: t("record.name"), cell: (c) => <Masked value={c.getValue() as string} label={m} /> },
    { accessorKey: "dob", header: t("record.dob"), cell: (c) => <Masked value={c.getValue() as string} label={m} /> },
    { accessorKey: "programme", header: t("record.programme") },
    {
      accessorKey: "status", header: t("record.status"),
      cell: (c) => <StatusBadge status={c.getValue() as string} label={t(`status.${c.getValue() as string}`)} />,
    },
    { id: "open", header: "", enableSorting: false,
      cell: (c) => <Link className="underline" href={`/institution/records/${c.row.original.id}`}>{t("record.open")}</Link> },
  ];

  return (
    <>
      <PageHeader title={t("nav.records")} description={t("record.intro")} />
      <div className="mb-4 flex items-center gap-2">
        <span className="text-sm">{t("record.filter")}</span>
        <Select value={status} onValueChange={(v) => { setStatus(v as string); setOffset(0); }}>
          <SelectTrigger className="w-48" aria-label={t("record.filter")}><SelectValue>{(v: string) => (v === "all" ? t("record.all") : t(`status.${v}`))}</SelectValue></SelectTrigger>
          <SelectContent>
            {STATUSES.map((s) => (
              <SelectItem key={s} value={s}>{s === "all" ? t("record.all") : t(`status.${s}`)}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <DataTable caption={t("nav.records")}
        columns={columns} data={q.data?.items ?? []} loading={q.isPending && !!id}
        error={q.isError ? t("error.generic") : null} onRetry={() => q.refetch()}
        labels={{ empty: t("record.empty"), error: t("error.generic"), retry: t("state.retry"), prev: t("table.prev"), next: t("table.next") }}
        paging={{ total: q.data?.total ?? 0, limit: LIMIT, offset, onOffset: setOffset }}
      />
    </>
  );
}

export default function Page() {
  return (
    <RoleGuard roles={["INSTITUTION_ADMIN", "INSTITUTION_STAFF"]}>
      <Records />
    </RoleGuard>
  );
}
