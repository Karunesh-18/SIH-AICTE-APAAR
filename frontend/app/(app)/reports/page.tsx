"use client";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { FilterSelect } from "@/components/filter-select";
import { PageHeader } from "@/components/page-header";
import { QueryError } from "@/components/query-error";
import { RoleGuard } from "@/components/role-guard";
import { EmptyState, ErrorState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import en from "@/lib/i18n/en.json";
import { useAuth } from "@/lib/auth";
import { csvFilename, reportQuery, saveBlob } from "@/lib/dash";
import type { InstitutionRow, RegionRow, ReportDef, ReportResult, SavedReport } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";

const TYPES = Object.keys(en).filter((k) => k.startsWith("inst.type.")).map((k) => k.slice("inst.type.".length));
const GROUPS = ["programme", "institution", "programme_type", "region"];
const cell = (v: unknown) => (v === null || v === undefined ? "" : String(v));

function Reports() {
  const { t, user } = useAuth();
  const qc = useQueryClient();
  const institutionUser = user?.role === "INSTITUTION_ADMIN" || user?.role === "INSTITUTION_STAFF";
  const cat = useApiQuery<ReportDef[]>("/reports");
  const saved = useApiQuery<SavedReport[]>("/reports/saved");
  const regions = useApiQuery<RegionRow[]>("/regions", { enabled: !institutionUser });
  const insts = useApiQuery<InstitutionRow[]>("/institutions", { enabled: !institutionUser });

  const [key, setKey] = useState("");
  const [f, setF] = useState<Record<string, string>>({});
  const [result, setResult] = useState<ReportResult | null>(null);
  const [state, setState] = useState<"idle" | "running" | "error">("idle");
  const [name, setName] = useState("");

  const def = cat.data?.find((r) => r.key === (key || cat.data?.[0]?.key));
  const activeKey = def?.key ?? "";
  const has = (k: string) => def?.filters.includes(k);
  const set = (k: string, v: string) => setF((p) => ({ ...p, [k]: v }));
  const filters = Object.fromEntries(Object.entries(f).filter(([k, v]) => v && def?.filters.includes(k)));

  async function run(k = activeKey, fl: Record<string, string> = filters) {
    setState("running");
    try {
      setResult(await api.get<ReportResult>(`/reports/${k}?${reportQuery(fl, "json")}`));
      setState("idle");
    } catch {
      setState("error");
    }
  }
  async function exportCsv() {
    try {
      saveBlob(await api.blob(`/reports/${activeKey}?${reportQuery(filters, "csv")}`), csvFilename(activeKey));
      toast.success(t("reports.exported"));
    } catch {
      toast.error(t("error.action"));
    }
  }
  async function save() {
    if (!name.trim()) return;
    try {
      await api.post("/reports", { name: name.trim(), report_key: activeKey, filters });
      setName("");
      qc.invalidateQueries({ queryKey: ["api", "/reports/saved"] });
    } catch {
      toast.error(t("error.action"));
    }
  }
  function rerun(s: SavedReport) {
    const fl = Object.fromEntries(Object.entries(s.filters).map(([k, v]) => [k, String(v)]));
    setKey(s.report_key);
    setF(fl);
    run(s.report_key, fl);
  }

  const cols = result?.columns ?? [];
  const rows = (result?.rows ?? []) as Record<string, unknown>[];

  return (
    <>
      <PageHeader title={t("reports.title")} description={t("reports.intro")} />
      {cat.isError && <QueryError error={cat.error} onRetry={() => cat.refetch()} />}
      {cat.isPending && <Skeleton className="h-24 w-full max-w-2xl" />}
      {def && (
        <form role="search" className="mb-4 flex flex-col gap-5" onSubmit={(e) => { e.preventDefault(); run(); }}>
          <fieldset className="flex flex-col gap-3">
            <legend className="t-eyebrow mb-2">{t("reports.sectionReport")}</legend>
            <FilterSelect id="r-key" label={t("reports.pick")} value={activeKey} onChange={(v) => { setKey(v); setResult(null); }}
                          options={(cat.data ?? []).map((r) => ({ value: r.key, label: r.title }))} noAny wide />
          </fieldset>
          <fieldset className="flex flex-col gap-3">
            <legend className="t-eyebrow mb-2">{t("reports.sectionFilters")}</legend>
            <div className="flex flex-wrap items-end gap-3">
              {has("region") && !institutionUser && (
                <FilterSelect id="r-region" label={t("filter.region")} value={f.region ?? ""} onChange={(v) => set("region", v)} any={t("filter.allRegions")}
                              options={(regions.data ?? []).map((r) => ({ value: r.code, label: r.name }))} />)}
              {has("type") && !institutionUser && (
                <FilterSelect id="r-type" label={t("filter.type")} value={f.type ?? ""} onChange={(v) => set("type", v)} any={t("filter.any")}
                              options={TYPES.map((v) => ({ value: v, label: t(`inst.type.${v}`) }))} />)}
              {has("institution_id") && !institutionUser && (
                <FilterSelect id="r-inst" label={t("filter.institution")} value={f.institution_id ?? ""} onChange={(v) => set("institution_id", v)} any={t("filter.allInstitutions")}
                              options={(insts.data ?? []).map((i) => ({ value: i.id, label: i.name }))} />)}
              {has("cycle_year") && (
                <div className="flex flex-col gap-1">
                  <Label htmlFor="r-cycle">{t("filter.cycle")}</Label>
                  <Input id="r-cycle" type="number" min={2000} className="min-h-11 w-28" value={f.cycle_year ?? ""} onChange={(e) => set("cycle_year", e.target.value)} />
                </div>)}
              {has("group_by") && (
                <FilterSelect id="r-group" label={t("reports.groupBy")} value={f.group_by ?? ""} onChange={(v) => set("group_by", v)} any={t("reports.group.programme")}
                              options={GROUPS.map((g) => ({ value: g, label: t(`reports.group.${g}`) }))} />)}
              <Button type="button" variant="ghost" className="min-h-11" disabled={Object.keys(filters).length === 0}
                      onClick={() => { setF({}); setResult(null); }}>{t("reports.reset")}</Button>
            </div>
          </fieldset>
          <div className="flex flex-wrap gap-3 border-t border-border pt-4">
            <Button type="submit" size="lg" className="min-h-11" disabled={state === "running"}>{state === "running" ? t("state.running") : t("reports.run")}</Button>
            <Button type="button" size="lg" variant="outline" className="min-h-11" onClick={exportCsv}>{t("reports.export")}</Button>
          </div>
        </form>
      )}
      {institutionUser && <p className="mb-4 text-xs text-muted-foreground">{t("reports.scopeNote")}</p>}

      {state === "error" && <ErrorState message={t("error.generic")} retryLabel={t("state.retry")} onRetry={() => run()} />}
      {state !== "error" && !result && def && <EmptyState title={t("reports.notRun")} />}
      {state !== "error" && result && (rows.length === 0 ? <EmptyState title={t("reports.empty")} /> : (
        <div className="overflow-x-auto rounded-md border border-border">
          <Table className="tabular-nums">
            <TableHeader><TableRow>{cols.map((c) => <TableHead key={c}>{c.replaceAll("_", " ")}</TableHead>)}</TableRow></TableHeader>
            <TableBody>{rows.map((r, i) => (
              <TableRow key={i}>{cols.map((c) => <TableCell key={c}>{cell(r[c])}</TableCell>)}</TableRow>
            ))}</TableBody>
          </Table>
        </div>
      ))}

      {def && (
        <div className="mt-4 flex flex-wrap items-end gap-2">
          <div className="flex flex-col gap-1">
            <Label htmlFor="r-name">{t("reports.saveName")}</Label>
            <Input id="r-name" className="min-h-11 w-64" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <Button variant="outline" className="min-h-11" disabled={!name.trim()} onClick={save}>{t("reports.save")}</Button>
        </div>
      )}

      <section aria-labelledby="sv-h" className="mt-8">
        <h2 id="sv-h" className="t-section mb-2">{t("reports.saved")}</h2>
        {saved.isError ? <QueryError error={saved.error} onRetry={() => saved.refetch()} /> :
          saved.isPending ? <Skeleton className="h-10 w-full max-w-md" /> :
            saved.data.length === 0 ? <p className="text-sm text-muted-foreground">{t("reports.savedEmpty")}</p> : (
              <ul className="flex flex-col gap-2">
                {saved.data.map((s) => (
                  <li key={s.id} className="flex items-center gap-3 text-sm">
                    <span className="font-medium">{s.name}</span>
                    <span className="text-muted-foreground">{cat.data?.find((r) => r.key === s.report_key)?.title ?? s.report_key}</span>
                    <Button size="sm" variant="outline" className="min-h-11" onClick={() => rerun(s)}>{t("reports.rerun")}</Button>
                  </li>
                ))}
              </ul>
            )}
      </section>
    </>
  );
}

export default function Page() {
  return (
    <RoleGuard roles={["AICTE_ADMIN", "AICTE_OFFICER", "INSTITUTION_ADMIN", "INSTITUTION_STAFF"]}>
      <Reports />
    </RoleGuard>
  );
}
