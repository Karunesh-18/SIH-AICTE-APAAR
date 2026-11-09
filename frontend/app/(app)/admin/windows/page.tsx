"use client";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { QueryError } from "@/components/query-error";
import { RoleGuard } from "@/components/role-guard";
import { EmptyState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { selectClass } from "@/components/filter-select";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fromLocalInput, ladderValid, toLocalInput, type LadderStep } from "@/lib/dash";
import { formatDateTime } from "@/lib/status";
import type { AdminWindow, CycleResult } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";

const TYPES = ["ENGINEERING", "MANAGEMENT", "PHARMACY", "OTHER"];
const AUD = ["institution", "officer", "admin"] as const;
type Draft = { id: string | null; cycle_year: string; type: string; opens: string; closes: string; ladder: LadderStep[] };

const blank = (): Draft => ({ id: null, cycle_year: String(new Date().getFullYear()), type: "", opens: "", closes: "",
  ladder: [{ step: "reminder", offset_hours: -72, audience: "institution" }] });

function Windows() {
  const { t } = useAuth();
  const qc = useQueryClient();
  const q = useApiQuery<AdminWindow[]>("/admin/windows");
  const [d, setD] = useState<Draft | null>(null);
  const [busy, setBusy] = useState("");
  const [cycle, setCycle] = useState<CycleResult | null>(null);
  const [anomaly, setAnomaly] = useState<number | null>(null);

  const edit = (w: AdminWindow) => setD({ id: w.id, cycle_year: String(w.cycle_year), type: w.institution_type ?? "",
    opens: toLocalInput(w.opens_at), closes: toLocalInput(w.closes_at), ladder: w.ladder.map((s) => ({ ...s })) });
  const patchStep = (i: number, p: Partial<LadderStep>) => d && setD({ ...d, ladder: d.ladder.map((s, j) => (j === i ? { ...s, ...p } : s)) });
  const valid = !!d && !!d.opens && !!d.closes && d.closes > d.opens && Number(d.cycle_year) > 0 && ladderValid(d.ladder);

  async function save() {
    if (!d || !valid) return;
    setBusy("save");
    const body = { cycle_year: Number(d.cycle_year), institution_type: d.type || null, opens_at: fromLocalInput(d.opens),
      closes_at: fromLocalInput(d.closes), ladder: d.ladder.map((s) => ({ ...s, step: s.step.trim() })) };
    try {
      if (d.id) await api.put(`/admin/windows/${d.id}`, body); else await api.post("/admin/windows", body);
      toast.success(t("windows.saved"));
      setD(null);
      qc.invalidateQueries({ queryKey: ["api", "/admin/windows"] });
    } catch {
      toast.error(t("error.action"));
    }
    setBusy("");
  }
  async function runCycle() {
    setBusy("cycle");
    try { setCycle(await api.post<CycleResult>("/admin/windows/run-cycle")); } catch { toast.error(t("error.action")); }
    setBusy("");
  }
  async function runAnomaly() {
    setBusy("anomaly");
    try { setAnomaly((await api.post<{ raised: number }>("/admin/anomaly/run")).raised); } catch { toast.error(t("error.action")); }
    setBusy("");
  }

  const field = (id: string, label: string, el: React.ReactNode) => <div className="flex flex-col gap-1"><Label htmlFor={id}>{label}</Label>{el}</div>;

  return (
    <>
      <PageHeader title={t("windows.title")} description={t("windows.intro")}
                  actions={<Button onClick={() => setD(blank())}>{t("windows.new")}</Button>} />
      <div className="mb-6 flex flex-wrap items-start gap-3">
        <Button variant="outline" disabled={!!busy} onClick={runCycle}>{busy === "cycle" ? t("state.running") : t("windows.runCycle")}</Button>
        <Button variant="outline" disabled={!!busy} onClick={runAnomaly}>{busy === "anomaly" ? t("state.running") : t("windows.runAnomaly")}</Button>
      </div>
      <div aria-live="polite" className="mb-6 flex flex-col gap-3">
        {cycle && (
          <section className="rounded-md border border-border p-3 text-sm">
            <h2 className="font-semibold">{t("windows.cycleResult")}</h2>
            <p className="tabular-nums">{t("windows.sent")}: {cycle.sent} - {t("windows.skipped")}: {cycle.skipped}</p>
            <p>{t("windows.late")}: {cycle.late.length ? cycle.late.join(", ") : t("windows.lateNone")}</p>
          </section>
        )}
        {anomaly !== null && <p className="rounded-md border border-border p-3 text-sm tabular-nums">{t("windows.anomalyResult")}: {anomaly}</p>}
      </div>

      {d && (
        <form className="mb-8 flex flex-col gap-4 rounded-md border border-border p-4" onSubmit={(e) => { e.preventDefault(); save(); }}>
          <div className="flex flex-wrap gap-3">
            {field("w-cycle", t("filter.cycle"), <Input id="w-cycle" type="number" className="w-28" value={d.cycle_year} onChange={(e) => setD({ ...d, cycle_year: e.target.value })} />)}
            {field("w-type", t("col.type"), (
              <select id="w-type" className={selectClass} value={d.type} onChange={(e) => setD({ ...d, type: e.target.value })}>
                <option value="">{t("windows.allTypes")}</option>
                {TYPES.map((v) => <option key={v} value={v}>{t(`inst.type.${v}`)}</option>)}
              </select>))}
            {field("w-open", t("windows.opens"), <Input id="w-open" type="datetime-local" className="w-52" value={d.opens} onChange={(e) => setD({ ...d, opens: e.target.value })} />)}
            {field("w-close", t("windows.closes"), <Input id="w-close" type="datetime-local" className="w-52" value={d.closes} onChange={(e) => setD({ ...d, closes: e.target.value })} />)}
          </div>
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-1 font-medium">{t("windows.ladder")}</legend>
            {d.ladder.map((s, i) => (
              <div key={i} className="flex flex-wrap items-end gap-2">
                {field(`s-n${i}`, t("windows.step"), <Input id={`s-n${i}`} className="w-40" value={s.step} onChange={(e) => patchStep(i, { step: e.target.value })} />)}
                {field(`s-o${i}`, t("windows.offset"), <Input id={`s-o${i}`} type="number" className="w-28" value={s.offset_hours} onChange={(e) => patchStep(i, { offset_hours: Number(e.target.value) })} />)}
                {field(`s-a${i}`, t("windows.audience"), (
                  <select id={`s-a${i}`} className={selectClass} value={s.audience} onChange={(e) => patchStep(i, { audience: e.target.value as LadderStep["audience"] })}>
                    {AUD.map((a) => <option key={a} value={a}>{t(`windows.aud.${a}`)}</option>)}
                  </select>))}
                <Button type="button" variant="outline" size="sm" onClick={() => setD({ ...d, ladder: d.ladder.filter((_, j) => j !== i) })}>{t("windows.removeStep")}</Button>
              </div>
            ))}
            <div><Button type="button" variant="outline" size="sm" onClick={() => setD({ ...d, ladder: [...d.ladder, { step: "", offset_hours: 0, audience: "institution" }] })}>{t("windows.addStep")}</Button></div>
          </fieldset>
          {!valid && <p role="status" className="text-sm text-muted-foreground">{t("windows.invalid")}</p>}
          <div className="flex gap-2">
            <Button type="submit" disabled={!valid || busy === "save"}>{busy === "save" ? t("state.saving") : t("windows.save")}</Button>
            <Button type="button" variant="outline" onClick={() => setD(null)}>{t("windows.cancel")}</Button>
          </div>
        </form>
      )}

      {q.isPending && <Skeleton className="h-24 w-full" />}
      {q.isError && <QueryError error={q.error} onRetry={() => q.refetch()} />}
      {q.data && q.data.length === 0 && <EmptyState title={t("windows.empty")} />}
      {q.data && q.data.length > 0 && (
        <ul className="flex flex-col gap-3">
          {q.data.map((w) => (
            <li key={w.id} className="rounded-md border border-border p-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-medium">{w.cycle_year} - {w.institution_type ? t(`inst.type.${w.institution_type}`) : t("windows.allTypes")}</p>
                <Button size="sm" variant="outline" onClick={() => edit(w)}>{t("windows.edit")}</Button>
              </div>
              <p className="tabular-nums text-muted-foreground">{formatDateTime(w.opens_at)} to {formatDateTime(w.closes_at)}</p>
              <p className="mt-1 text-muted-foreground">
                {t("windows.ladder")}: {w.ladder.map((s) => `${s.step} (${s.offset_hours}h, ${t(`windows.aud.${s.audience}`)})`).join("; ") || "-"}
              </p>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

export default function Page() {
  return (
    <RoleGuard roles={["AICTE_ADMIN"]}>
      <Windows />
    </RoleGuard>
  );
}
