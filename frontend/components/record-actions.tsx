"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { toast } from "sonner";
import { Masked } from "@/components/masked";
import { NoteDialog } from "@/components/note-dialog";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { buildCorrection, type CorrectionForm } from "@/lib/correction";
import type { CorrectionResult, FlagBrief, RecordDetail } from "@/lib/types";

const blank: CorrectionForm = { apaar_id: "", name: "", dob: "", year_of_study: "", admission_date: "", admission_category: "" };

function Briefs({ title, items, none }: { title: string; items: FlagBrief[]; none: string }) {
  return (
    <div>
      <p className="font-medium">{title}</p>
      {items.length === 0 ? <p className="text-muted-foreground">{none}</p> : (
        <ul className="mt-1 flex flex-col gap-1">
          {items.map((f) => <li key={f.id}><span className="font-mono">{f.rule_code}</span> {f.reason}</li>)}
        </ul>
      )}
    </div>
  );
}

export function RecordActions({ record }: { record: RecordDetail }) {
  const { t } = useAuth();
  const qc = useQueryClient();
  const path = `/records/${record.id}`;
  const [form, setForm] = useState<CorrectionForm>(blank);
  const [err, setErr] = useState(false);
  const [result, setResult] = useState<CorrectionResult | null>(null);
  const [withdrawing, setWithdrawing] = useState(false);
  const pending = record.status === "pending_apaar";
  const m = t("record.masked");
  const fail = (e: unknown) => toast.error(e instanceof ApiError ? e.message : t("error.generic"));

  const correct = useMutation({
    mutationFn: (body: Record<string, string | number>) => api.patch<CorrectionResult>(path, body),
    onSuccess: (r) => {
      setResult(r); setForm(blank); setErr(false);
      toast.success(t("corr.result"));
      qc.invalidateQueries({ queryKey: ["api", path] });
    },
    onError: fail,
  });
  const withdraw = useMutation({
    mutationFn: (reason: string) => api.post(`${path}/withdraw`, { reason }),
    onSuccess: () => { setWithdrawing(false); toast.success(t("withdraw.done")); qc.invalidateQueries({ queryKey: ["api", path] }); },
    onError: (e) => { setWithdrawing(false); fail(e); },
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const body = buildCorrection(form);
    setErr(!body);
    if (body) correct.mutate(body);
  };
  const field = (k: keyof CorrectionForm, label: string, type = "text") => (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={`c-${k}`}>{label}</Label>
      <Input id={`c-${k}`} type={type} value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
    </div>
  );

  if (record.status === "withdrawn" || !record.is_current) return null;
  return (
    <section aria-labelledby="co-h" className="flex flex-col gap-4">
      <h2 id="co-h" className="font-semibold">{pending ? t("corr.addApaar") : t("corr.title")}</h2>
      <p className="max-w-prose text-sm text-muted-foreground">{pending ? t("corr.pendingHint") : t("corr.hint")}</p>
      <form onSubmit={submit} className="grid max-w-2xl gap-3 sm:grid-cols-2">
        {field("apaar_id", t("corr.apaar"))}
        {!pending && <>
          {field("name", t("corr.name"))}
          {field("dob", t("corr.dob"), "date")}
          {field("year_of_study", t("corr.yos"), "number")}
          {field("admission_date", t("corr.admission"), "date")}
          {field("admission_category", t("corr.category"))}
        </>}
        <div className="flex flex-wrap items-center gap-3 sm:col-span-2">
          <Button type="submit" disabled={correct.isPending}>{pending ? t("corr.addApaar") : t("corr.save")}</Button>
          {err && <p role="alert" className="text-sm text-status-excess">{t("corr.nochange")}</p>}
        </div>
      </form>

      {result && (
        <div role="status" className="flex max-w-3xl flex-col gap-4 rounded-md border border-border p-4 text-sm">
          <p className="font-semibold">{t("corr.result")}</p>
          <div className="grid gap-3 sm:grid-cols-2">
            {([["corr.before", result.previous], ["corr.after", result.record]] as const).map(([k, r]) => (
              <div key={k} className="rounded-md bg-muted/50 p-3">
                <p className="flex items-center gap-2 font-medium">{t(k)} - {t("record.version")} {r.version}
                  <StatusBadge status={r.status} label={t(`status.${r.status}`)} /></p>
                <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 tabular-nums">
                  <dt className="text-muted-foreground">{t("record.apaar")}</dt><dd><Masked value={r.apaar_id} label={m} /></dd>
                  <dt className="text-muted-foreground">{t("record.name")}</dt><dd><Masked value={r.name} label={m} /></dd>
                  <dt className="text-muted-foreground">{t("record.dob")}</dt><dd><Masked value={r.dob} label={m} /></dd>
                  <dt className="text-muted-foreground">{t("record.admission")}</dt><dd>{r.admission_date}</dd>
                </dl>
              </div>
            ))}
          </div>
          <Briefs title={t("corr.closed")} items={result.closed_flags} none={t("corr.none")} />
          <Briefs title={t("corr.raised")} items={result.raised_flags} none={t("corr.clean")} />
          <Link className="underline" href={`/institution/records/${result.record.id}`}>{t("record.detail")}</Link>
        </div>
      )}

      <div>
        <Button variant="outline" onClick={() => setWithdrawing(true)}>{t("withdraw.button")}</Button>
      </div>
      {withdrawing && (
        <NoteDialog open t={t} destructive title="withdraw.title" label="withdraw.reason" confirmLabel="withdraw.button"
                    description={t("withdraw.body")} pending={withdraw.isPending}
                    onClose={() => setWithdrawing(false)} onSubmit={(r) => withdraw.mutate(r)} />
      )}
    </section>
  );
}
