"use client";
import { useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { CheckGroup, FieldError } from "@/components/consent-parts";
import { DataTable, type Col } from "@/components/data-table";
import { ToneBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { FIELDS, PURPOSES, consentStatus, fieldLabelKey, validateConsent } from "@/lib/consent";
import { consentMeta, formatDateTime } from "@/lib/status";
import type { Consent } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";

const EMPTY = { apaar_id: "", purposes: [] as string[], fields: [] as string[], source: "", expires_at: "" };

export function ConsentsManager() {
  const { t } = useAuth();
  const qc = useQueryClient();
  const [lookup, setLookup] = useState("");
  const [applied, setApplied] = useState("");
  const path = `/consents?limit=100${applied ? `&apaar=${encodeURIComponent(applied)}` : ""}`;
  const list = useApiQuery<{ items: Consent[] }>(path);
  const [f, setF] = useState(EMPTY);
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [target, setTarget] = useState<Consent | null>(null);
  const [now] = useState(() => new Date());
  const set = <K extends keyof typeof EMPTY>(k: K, v: (typeof EMPTY)[K]) => setF((p) => ({ ...p, [k]: v }));
  const e = (k: string) => (errs[k] ? t(errs[k]) : undefined);

  async function submit(ev: FormEvent) {
    ev.preventDefault();
    const found = validateConsent(f, new Date());
    setErrs(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    setProblem(null);
    try {
      await api.post("/consents", {
        apaar_id: f.apaar_id.trim(), purposes: f.purposes, fields: f.fields, source: f.source.trim(),
        expires_at: new Date(`${f.expires_at}T23:59:59`).toISOString(),
      });
      toast.success(t("consent.recorded"));
      setF(EMPTY);
      qc.invalidateQueries({ queryKey: ["api"] });
    } catch (err) {
      const s = err instanceof ApiError ? err.status : 0;
      setProblem(s === 403 || s === 404 ? t("consent.notYourStudent") : s === 422 || s === 400 ? t("consent.invalidRequest") : t("error.generic"));
    }
    setBusy(false);
  }

  async function withdraw() {
    if (!target) return;
    setBusy(true);
    try {
      await api.del(`/consents/${target.id}`);
      toast.success(t("consent.withdrawn"));
      qc.invalidateQueries({ queryKey: ["api"] });
    } catch {
      toast.error(t("error.action"));
    }
    setTarget(null);
    setBusy(false);
  }

  const columns: Col<Consent>[] = [
    { accessorKey: "apaar_id", header: t("col.apaar"), cell: (c) => <span className="font-mono">{c.getValue() as string}</span> },
    { accessorKey: "purposes", header: t("col.purpose"), enableSorting: false, cell: (c) => (c.getValue() as string[]).map((p) => t(`purpose.${p}`)).join(", ") },
    { accessorKey: "fields", header: t("col.fields"), enableSorting: false, cell: (c) => (c.getValue() as string[]).map((x) => t(fieldLabelKey(x))).join(", ") },
    { accessorKey: "source", header: t("consent.source") },
    { accessorKey: "given_at", header: t("consent.given"), cell: (c) => formatDateTime(c.getValue() as string) },
    { accessorKey: "expires_at", header: t("col.expires"), cell: (c) => formatDateTime(c.getValue() as string) },
    { id: "status", header: t("col.status"), accessorFn: (r) => consentStatus(r, now), cell: (c) => {
      const m = consentMeta(c.getValue() as string);
      return <ToneBadge meta={m} label={t(m.labelKey)} />;
    } },
    { id: "actions", header: t("col.actions"), enableSorting: false, cell: (c) => {
      const row = c.row.original;
      return consentStatus(row, now) === "withdrawn" ? null : (
        <Button variant="outline" size="sm" onClick={() => setTarget(row)}>{t("consent.withdraw")}</Button>
      );
    } },
  ];

  return (
    <div className="flex flex-col gap-8">
      <form onSubmit={submit} noValidate className="flex max-w-xl flex-col gap-4" aria-labelledby="c-new">
        <h2 id="c-new" className="text-base font-semibold">{t("consent.new")}</h2>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="c-apaar">{t("consent.apaar")}</Label>
          <Input id="c-apaar" inputMode="numeric" autoComplete="off" value={f.apaar_id} aria-invalid={!!errs.apaar_id} onChange={(x) => set("apaar_id", x.target.value)} />
          <FieldError msg={e("apaar_id")} />
        </div>
        <CheckGroup legend={t("consent.purposes")} value={f.purposes} onChange={(v) => set("purposes", v)} error={e("purposes")}
          options={PURPOSES.map((p) => ({ value: p, label: t(`purpose.${p}`), desc: t(`purpose.${p}.desc`) }))} />
        <CheckGroup legend={t("consent.fields")} hint={t("consent.fieldsHint")} value={f.fields} onChange={(v) => set("fields", v)} error={e("fields")}
          options={FIELDS.map((x) => ({ value: x, label: t(fieldLabelKey(x)) }))} />
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="c-source">{t("consent.source")}</Label>
          <Input id="c-source" maxLength={64} value={f.source} aria-invalid={!!errs.source} aria-describedby="c-source-h" onChange={(x) => set("source", x.target.value)} />
          <p id="c-source-h" className="text-xs text-muted-foreground">{t("consent.sourceHint")}</p>
          <FieldError msg={e("source")} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="c-exp">{t("consent.expires")}</Label>
          <Input id="c-exp" type="date" className="w-44" value={f.expires_at} aria-invalid={!!errs.expires_at} onChange={(x) => set("expires_at", x.target.value)} />
          <FieldError msg={e("expires_at")} />
        </div>
        {problem && <p role="alert" className="text-sm text-status-excess">{problem}</p>}
        <Button type="submit" disabled={busy} className="w-fit">{t("consent.submit")}</Button>
      </form>

      <section aria-labelledby="c-list" className="flex flex-col gap-3">
        <h2 id="c-list" className="text-base font-semibold">{t("consent.list")}</h2>
        <form className="flex flex-wrap items-end gap-2" onSubmit={(ev) => { ev.preventDefault(); setApplied(lookup.trim()); }}>
          <div className="flex flex-col gap-1">
            <Label htmlFor="c-lookup">{t("consent.lookup")}</Label>
            <Input id="c-lookup" className="w-56" inputMode="numeric" value={lookup} onChange={(x) => setLookup(x.target.value)} />
          </div>
          <Button type="submit" variant="outline" size="sm">{t("consent.lookupBtn")}</Button>
          {applied && <Button type="button" variant="outline" size="sm" onClick={() => { setApplied(""); setLookup(""); }}>{t("filter.clear")}</Button>}
        </form>
        <DataTable columns={columns} caption={t("nav.consents")} data={list.data?.items ?? []} loading={list.isPending} onRetry={() => list.refetch()}
          error={list.isError ? t(list.error.status === 403 ? "error.forbidden" : "error.generic") : null}
          labels={{ empty: t("consent.empty"), error: t("error.generic"), retry: t("state.retry"), prev: t("table.prev"), next: t("table.next") }} />
      </section>

      <ConfirmDialog open={!!target} title={t("consent.withdrawTitle")} body={target ? `${t("col.apaar")} ${target.apaar_id}; ${t("col.purpose")}: ${target.purposes.map((p) => t(`purpose.${p}`)).join(", ")}. ${t("consent.withdrawBody")}` : ""} confirmLabel={t("consent.withdrawConfirm")}
        cancelLabel={t("dialog.cancel")} pending={busy} onConfirm={withdraw} onClose={() => setTarget(null)} />
    </div>
  );
}
