"use client";
import { useQueryClient } from "@tanstack/react-query";
import { QRCodeSVG } from "qrcode.react";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";
import { CheckCircle2, ShieldAlert, XOctagon } from "lucide-react";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { CheckGroup, CopyButton, FieldError } from "@/components/consent-parts";
import { DataTable, type Col } from "@/components/data-table";
import { selectClass } from "@/components/filter-select";
import { QueryError } from "@/components/query-error";
import { ToneBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fieldLabelKey, formatFieldValue, refusalKey, validateRequest, verifyUrl } from "@/lib/consent";
import { formatDateTime, outcomeMeta } from "@/lib/status";
import type { Policies, VerificationGranted, VerificationResult, VerificationRow } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";

const LIST = "/verifications?limit=50";

function GrantedCard({ r, onRevoked }: { r: VerificationGranted; onRevoked: () => void }) {
  const { t } = useAuth();
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [revoked, setRevoked] = useState(false);
  const link = verifyUrl(window.location.origin, r.token);

  async function revoke() {
    setBusy(true);
    try {
      await api.post(`/verifications/${r.id}/revoke`);
      setRevoked(true);
      setConfirm(false);
      toast.success(t("vr.revokeDone"));
      onRevoked();
    } catch {
      toast.error(t("error.action"));
    }
    setBusy(false);
  }

  return (
    <section aria-labelledby="granted-h" className="flex max-w-2xl flex-col gap-4 rounded-md border border-status-clear/40 p-4">
      <h2 id="granted-h" className="flex items-center gap-2 font-semibold text-status-clear">
        <CheckCircle2 aria-hidden className="size-5" />{t("vr.granted")}
        <span className="font-normal text-muted-foreground">({t(`purpose.${r.purpose}`)})</span>
      </h2>
      <div>
        <h3 className="mb-1 text-sm font-medium">{t("vr.answer")}</h3>
        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-sm">
          {Object.entries(r.fields).map(([f, v]) => (
            <div key={f} className="contents">
              <dt className="text-muted-foreground">{t(fieldLabelKey(f))}</dt>
              <dd className="font-medium">{formatFieldValue(f, v)}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-2 text-xs text-muted-foreground">{t("verify.expiresAt")}: {formatDateTime(r.expires_at)}</p>
      </div>
      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="w-fit shrink-0 rounded-md border border-border bg-white p-2">
          <QRCodeSVG value={link} size={132} role="img" aria-label={t("vr.qrAlt")} />
        </div>
        <div className="flex min-w-0 flex-col gap-2">
          <p className="text-sm">{t("vr.qr")}</p>
          <h3 className="text-sm font-medium">{t("vr.token")}</h3>
          <code className="max-h-24 overflow-auto rounded bg-muted p-2 font-mono text-xs break-all">{r.token}</code>
          <p className="text-xs text-muted-foreground">{t("vr.tokenNote")}</p>
          <div className="flex flex-wrap gap-2">
            <CopyButton text={r.token} label={t("vr.copy")} doneLabel={t("vr.copied")} />
            <CopyButton text={link} label={t("vr.copyLink")} doneLabel={t("vr.copied")} />
            <Button variant="outline" size="sm" disabled={revoked} onClick={() => setConfirm(true)}>
              {revoked ? t("outcome.REVOKED") : t("vr.revoke")}
            </Button>
          </div>
        </div>
      </div>
      <ConfirmDialog open={confirm} title={t("vr.revokeTitle")} body={t("vr.revokeBody")} confirmLabel={t("vr.revoke")}
        cancelLabel={t("dialog.cancel")} pending={busy} onConfirm={revoke} onClose={() => setConfirm(false)} />
    </section>
  );
}

export function VerifierWorkspace() {
  const { t } = useAuth();
  const qc = useQueryClient();
  const policies = useApiQuery<Policies>("/policies");
  const mine = useApiQuery<{ items: VerificationRow[] }>(LIST);
  const [apaar, setApaar] = useState("");
  const [purpose, setPurpose] = useState("");
  const [fields, setFields] = useState<string[]>([]);
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const e = (k: string) => (errs[k] ? t(errs[k]) : undefined);

  const allowed = policies.data?.items.find((p) => p.purpose === purpose)?.allowed_fields ?? [];
  const pick = (p: string) => {
    setPurpose(p);
    const next = policies.data?.items.find((x) => x.purpose === p)?.allowed_fields ?? [];
    setFields((cur) => cur.filter((f) => next.includes(f)));
  };

  async function submit(ev: FormEvent) {
    ev.preventDefault();
    const found = validateRequest({ apaar_id: apaar, purpose, fields });
    setErrs(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    setProblem(null);
    setResult(null);
    try {
      setResult(await api.post<VerificationResult>("/verifications", { apaar_id: apaar.trim(), purpose, fields }));
      qc.invalidateQueries({ queryKey: ["api", LIST] });
    } catch (err) {
      const s = err instanceof ApiError ? err.status : 0;
      setProblem(s === 403 ? t("vr.notApproved") : s === 429 ? t("vr.limited") : t("error.generic"));
    }
    setBusy(false);
  }

  const columns: Col<VerificationRow>[] = [
    { accessorKey: "created_at", header: t("col.when"), cell: (c) => formatDateTime(c.getValue() as string) },
    { accessorKey: "purpose", header: t("col.purpose"), cell: (c) => t(`purpose.${c.getValue() as string}`) },
    { accessorKey: "outcome", header: t("col.outcome"), cell: (c) => {
      const m = outcomeMeta(c.row.original.outcome, c.row.original.revoked_at);
      return <ToneBadge meta={m} label={t(m.labelKey)} />;
    } },
    { accessorKey: "fields_requested", header: t("col.fields"), enableSorting: false,
      cell: (c) => (c.getValue() as string[]).map((f) => t(fieldLabelKey(f))).join(", ") },
    { accessorKey: "refusal_reason", header: t("col.reason"), enableSorting: false,
      cell: (c) => (c.getValue() ? t(refusalKey(c.getValue() as string)) : "-") },
    { accessorKey: "expires_at", header: t("col.expires"), cell: (c) => formatDateTime(c.getValue() as string | null) },
  ];

  if (policies.isError && policies.error.status === 403) {
    return <div role="alert" className="flex items-center gap-2 rounded-md border border-border p-4 text-sm"><ShieldAlert aria-hidden className="size-5" />{t("vr.notApproved")}</div>;
  }

  return (
    <div className="flex flex-col gap-8">
      <form onSubmit={submit} noValidate className="flex max-w-xl flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="v-apaar">{t("vr.apaar")}</Label>
          <Input id="v-apaar" inputMode="numeric" autoComplete="off" value={apaar} aria-invalid={!!errs.apaar_id} onChange={(x) => setApaar(x.target.value)} />
          <FieldError msg={e("apaar_id")} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="v-purpose">{t("vr.purpose")}</Label>
          <select id="v-purpose" className={selectClass} value={purpose} aria-invalid={!!errs.purpose} onChange={(x) => pick(x.target.value)}>
            <option value="">{t("vr.purposeChoose")}</option>
            {policies.data?.items.map((p) => <option key={p.purpose} value={p.purpose}>{t(`purpose.${p.purpose}`)}</option>)}
          </select>
          {purpose && <p className="text-sm text-muted-foreground">{t(`purpose.${purpose}.desc`)}</p>}
          <FieldError msg={e("purpose")} />
        </div>
        {policies.isPending && <Skeleton className="h-20 w-full" />}
        {policies.isError && policies.error.status !== 403 && <QueryError error={policies.error} onRetry={() => policies.refetch()} />}
        {policies.data && (
          !purpose ? <p className="text-sm text-muted-foreground">{t("vr.fieldsNone")}</p>
          : allowed.length === 0 ? <p className="text-sm text-muted-foreground">{t("vr.fieldsEmpty")}</p>
          : <CheckGroup legend={t("vr.fields")} hint={t("vr.fieldsHint")} value={fields} onChange={setFields} error={e("fields")}
              options={allowed.map((f) => ({ value: f, label: t(fieldLabelKey(f)) }))} />
        )}
        {problem && <p role="alert" className="text-sm text-status-excess">{problem}</p>}
        <Button type="submit" disabled={busy || policies.isPending} className="w-fit">{busy ? t("vr.sending") : t("vr.submit")}</Button>
      </form>

      <div aria-live="polite">
        {result?.outcome === "GRANTED" && <GrantedCard r={result} onRevoked={() => qc.invalidateQueries({ queryKey: ["api", LIST] })} />}
        {result?.outcome === "REFUSED" && (
          <section role="alert" className="flex max-w-2xl flex-col gap-1 rounded-md border border-status-excess/40 bg-status-excess-bg p-4">
            <h2 className="flex items-center gap-2 font-semibold text-status-excess"><XOctagon aria-hidden className="size-5" />{t("vr.refused")}</h2>
            <p className="text-sm">{result.message}</p>
            {result.detail && result.detail.length > 0 && (
              <p className="text-sm text-muted-foreground">{result.detail.map((f) => t(fieldLabelKey(f))).join(", ")}</p>
            )}
          </section>
        )}
      </div>

      <section aria-labelledby="mine-h" className="flex flex-col gap-3">
        <h2 id="mine-h" className="text-base font-semibold">{t("vr.mine")}</h2>
        <DataTable columns={columns} caption={t("nav.verifications")} data={mine.data?.items ?? []} loading={mine.isPending} onRetry={() => mine.refetch()}
          error={mine.isError ? t("error.generic") : null}
          labels={{ empty: t("vr.mineEmpty"), error: t("error.generic"), retry: t("state.retry"), prev: t("table.prev"), next: t("table.next") }} />
      </section>
    </div>
  );
}
