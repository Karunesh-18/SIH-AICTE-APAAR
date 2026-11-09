"use client";
import { selectClass } from "@/components/filter-select";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Age, RuleChip, StateBadge } from "@/components/flag-parts";
import { DataTable, type Col } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth";
import { FLAG_STATES, RULE_CODES, filtersFromQuery, filtersToQuery, type Filters } from "@/lib/review";
import { formatDateTime } from "@/lib/status";
import type { FlagRow, InstitutionRow, Page, RegionRow } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";

const LIMIT = 25;
const sel = selectClass;

/** Flag list. Filters live in the URL query string so a view can be shared and survives reload. */
export function FlagQueue({ mode }: { mode: "aicte" | "institution" }) {
  const { t } = useAuth();
  const router = useRouter();
  const path = usePathname();
  const params = useSearchParams();
  const f = filtersFromQuery(new URLSearchParams(params.toString()));
  const aicte = mode === "aicte";
  const detail = aicte ? "/review" : "/institution/flags";

  const set = (patch: Partial<Filters>) => {
    const qs = filtersToQuery({ ...f, offset: 0, ...patch });
    router.replace(qs ? `${path}?${qs}` : path);
  };

  const api = new URLSearchParams(
    Object.entries({ state: f.state, rule: f.rule, institution: aicte ? f.institution : "", region: aicte ? f.region : "",
                     age_days: f.age_days, limit: String(LIMIT), offset: String(f.offset) }).filter(([, v]) => v));
  const q = useApiQuery<Page<FlagRow>>(`/flags?${api}`);
  const insts = useApiQuery<InstitutionRow[]>("/institutions", { enabled: aicte });
  const regions = useApiQuery<RegionRow[]>("/regions", { enabled: aicte });
  const active = f.state || f.rule || f.institution || f.region || f.age_days;

  const columns: Col<FlagRow>[] = [
    { accessorKey: "rule_code", header: t("col.rule"), cell: (c) => <RuleChip code={c.getValue() as string} /> },
    ...(aicte ? [{ accessorKey: "institution_name", header: t("col.institution") } as Col<FlagRow>] : []),
    { accessorKey: "state", header: t("col.state"), cell: (c) => <StateBadge state={c.getValue() as string} /> },
    { accessorKey: "age_days", header: t("col.age"), cell: (c) => <Age days={c.getValue() as number} /> },
    { accessorKey: "record_count", header: t("col.records") },
    { accessorKey: "created_at", header: t("col.raised"), cell: (c) => formatDateTime(c.getValue() as string) },
    { accessorKey: "reason", header: t("col.reason"), enableSorting: false,
      cell: (c) => (
        <Link className="line-clamp-2 max-w-md underline-offset-2 hover:underline" href={`${detail}/${c.row.original.id}`}>
          {c.getValue() as string}
        </Link>
      ) },
  ];

  const field = (id: string, label: string, el: React.ReactNode) => (
    <div className="flex flex-col gap-1"><Label htmlFor={id}>{label}</Label>{el}</div>
  );
  const any = <option value="">{t("filter.any")}</option>;

  return (
    <div className="flex flex-col gap-4">
      <form role="search" className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
        {field("f-state", t("filter.state"),
          <select id="f-state" className={sel} value={f.state} onChange={(e) => set({ state: e.target.value })}>
            {any}{FLAG_STATES.map((s) => <option key={s} value={s}>{t(`flag.state.${s}`)}</option>)}
          </select>)}
        {field("f-rule", t("filter.rule"),
          <select id="f-rule" className={sel} value={f.rule} onChange={(e) => set({ rule: e.target.value })}>
            {any}{RULE_CODES.map((r) => <option key={r} value={r}>{r} {t(`rule.${r}`)}</option>)}
          </select>)}
        {aicte && field("f-inst", t("filter.institution"),
          <select id="f-inst" className={`${sel} max-w-56`} value={f.institution} onChange={(e) => set({ institution: e.target.value })}>
            <option value="">{t("filter.allInstitutions")}</option>
            {(insts.data ?? []).map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
          </select>)}
        {aicte && field("f-region", t("filter.region"),
          <select id="f-region" className={sel} value={f.region} onChange={(e) => set({ region: e.target.value })}>
            <option value="">{t("filter.allRegions")}</option>
            {(regions.data ?? []).map((r) => <option key={r.id} value={r.code}>{r.name}</option>)}
          </select>)}
        {field("f-age", t("filter.age"),
          <Input id="f-age" type="number" min={0} className="w-28" defaultValue={f.age_days} key={`a${f.age_days}`}
                 onBlur={(e) => e.target.value !== f.age_days && set({ age_days: e.target.value })}
                 onKeyDown={(e) => e.key === "Enter" && set({ age_days: e.currentTarget.value })} />)}
        {active && <Button type="button" variant="outline" size="sm"
                           onClick={() => router.replace(path)}>{t("filter.clear")}</Button>}
      </form>
      <DataTable columns={columns} caption={t("nav.flags")} data={q.data?.items ?? []} loading={q.isPending} onRetry={() => q.refetch()}
                 error={q.isError ? t(q.error.status === 403 ? "error.forbidden" : "error.generic") : null}
                 paging={q.data ? { total: q.data.total, limit: LIMIT, offset: f.offset, onOffset: (offset) => set({ offset }) } : undefined}
                 labels={{ empty: t(aicte ? "review.empty" : "inst.flags.empty"), error: t("error.generic"),
                           retry: t("state.retry"), prev: t("table.prev"), next: t("table.next") }} />
    </div>
  );
}
