"use client";
import { useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { CheckCircle2, XOctagon } from "lucide-react";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { DataTable, type Col } from "@/components/data-table";
import { FilterSelect } from "@/components/filter-select";
import { PageHeader } from "@/components/page-header";
import { RoleGuard } from "@/components/role-guard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { filterAudit, type AuditFilters } from "@/lib/audit";
import { useAuth } from "@/lib/auth";
import { formatDateTime } from "@/lib/status";
import type { AuditRow, Checkpoint, CheckpointCheck, ClockState } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";

const LIMIT = 100;
const ROLES = ["AICTE_ADMIN", "AICTE_OFFICER", "INSTITUTION_ADMIN", "INSTITUTION_STAFF", "VERIFIER", "PUBLIC"];
type Chain = { ok: boolean; count: number; first_broken_id: number | null; checkpoint?: CheckpointCheck | null };
const CP_KEY = { missing_rows: "audit.cp.missing", hash_mismatch: "audit.cp.hash", bad_signature: "audit.cp.sig" } as const;
const short = (h: string) => h.slice(0, 12);

function Audit() {
  const { t } = useAuth();
  const qc = useQueryClient();
  const [offset, setOffset] = useState(0);
  const q = useApiQuery<{ items: AuditRow[]; total: number }>(`/admin/audit?limit=${LIMIT}&offset=${offset}`);
  // The clock endpoint reports whether the server is in demo mode, which is what enables the tamper demo.
  const clock = useApiQuery<ClockState>("/admin/clock");
  const demo = clock.data?.demo_mode === true;
  const [f, setF] = useState<AuditFilters>({});
  const [chain, setChain] = useState<Chain | null>(null);
  const [checking, setChecking] = useState(false);
  const [askTamper, setAskTamper] = useState(false);
  const [busy, setBusy] = useState(false);
  const cps = useApiQuery<Checkpoint[]>("/audit/checkpoints");
  const [created, setCreated] = useState<Checkpoint | null>(null);
  const [askTrunc, setAskTrunc] = useState(false);
  const [truncated, setTruncated] = useState<number | null>(null);
  const [tampered, setTampered] = useState<number | null>(null);
  const rows = useMemo(() => filterAudit(q.data?.items ?? [], f), [q.data, f]);
  const entities = useMemo(() => [...new Set((q.data?.items ?? []).map((r) => r.entity_type).filter(Boolean) as string[])].sort(), [q.data]);
  const set = (k: keyof AuditFilters, v: string) => setF((p) => ({ ...p, [k]: v }));

  async function verify() {
    setChecking(true);
    try {
      setChain(await api.post<Chain>("/admin/audit/verify"));
    } catch {
      toast.error(t("error.action"));
    }
    setChecking(false);
  }

  async function tamper() {
    setBusy(true);
    try {
      const r = await api.post<{ tampered_id: number }>("/admin/dev/tamper-audit");
      setTampered(r.tampered_id);
      setChain(null);
      qc.invalidateQueries({ queryKey: ["api"] });
    } catch {
      toast.error(t("error.action"));
    }
    setAskTamper(false);
    setBusy(false);
  }

  async function createCp() {
    setBusy(true);
    try {
      setCreated(await api.post<Checkpoint>("/admin/audit/checkpoint"));
      qc.invalidateQueries({ queryKey: ["api"] });
    } catch {
      toast.error(t("error.action"));
    }
    setBusy(false);
  }

  async function truncate() {
    setBusy(true);
    try {
      await api.post("/admin/dev/truncate-audit?n=3");
      setTruncated(3);
      setChain(null);
      qc.invalidateQueries({ queryKey: ["api"] });
    } catch {
      toast.error(t("error.action"));
    }
    setAskTrunc(false);
    setBusy(false);
  }

  const columns: Col<AuditRow>[] = [
    { accessorKey: "id", header: t("audit.colId") },
    { accessorKey: "occurred_at", header: t("audit.colWhen"), cell: (c) => formatDateTime(c.getValue() as string) },
    { accessorKey: "actor_role", header: t("audit.colActor"), cell: (c) => (c.getValue() as string | null) ?? "-" },
    { accessorKey: "action", header: t("audit.colAction"), cell: (c) => <span className="font-mono text-xs">{c.getValue() as string}</span> },
    { id: "entity", header: t("audit.colEntity"), accessorFn: (r) => `${r.entity_type ?? "-"} ${r.entity_id ?? ""}`.trim(),
      cell: (c) => <span className="font-mono text-xs break-all">{c.getValue() as string}</span> },
  ];

  return (
    <>
      <PageHeader title={t("audit.title")} description={t("audit.intro")}
        actions={<>
          <Button variant="outline" disabled={checking} onClick={verify}>{checking ? t("audit.verifying") : t("audit.verify")}</Button>
          <Button variant="outline" disabled={busy} onClick={createCp}>{t("audit.cp.create")}</Button>
          {demo && <Button variant="destructive" onClick={() => setAskTamper(true)}>{t("audit.tamper")} ({t("audit.tamperDemo")})</Button>}
          {demo && <Button variant="destructive" onClick={() => setAskTrunc(true)}>{t("audit.truncate")} ({t("audit.tamperDemo")})</Button>}
        </>} />
      <div aria-live="polite" className="mb-4 flex flex-col gap-2">
        {chain && (chain.ok ? (
          <p role="status" className="flex items-center gap-2 rounded-md border border-status-clear/40 bg-status-clear-bg p-3 text-sm text-status-clear">
            <CheckCircle2 aria-hidden className="size-5" />{t("audit.ok").replace("{n}", String(chain.count))}
          </p>
        ) : (
          <p role="alert" className="flex items-center gap-2 rounded-md border border-status-excess/40 bg-status-excess-bg p-3 text-sm text-status-excess">
            <XOctagon aria-hidden className="size-5" />{t("audit.broken").replace("{id}", String(chain.first_broken_id))}
          </p>
        ))}
        {chain && (
          <p role={chain.checkpoint && !chain.checkpoint.ok ? "alert" : "status"} className="text-sm">
            {!chain.checkpoint ? t("audit.cp.none")
              : chain.checkpoint.ok || !chain.checkpoint.reason ? t("audit.cp.ok")
              : t(CP_KEY[chain.checkpoint.reason]).replace("{seq}", String(cps.data?.[0]?.seq ?? ""))}
          </p>
        )}
        {created && (
          <p role="status" data-testid="cp-new" className="text-sm">
            {t("audit.cp.created").replace("{seq}", String(created.seq)).replace("{hash}", short(created.hash))
              .replace("{n}", String(created.count)).replace("{when}", formatDateTime(created.signed_at))}
          </p>
        )}
        {truncated !== null && <p role="status" className="text-sm text-muted-foreground">{t("audit.truncated").replace("{n}", String(truncated))}</p>}
        {tampered !== null && <p role="status" className="text-sm text-muted-foreground">{t("audit.tampered").replace("{id}", String(tampered))}</p>}
      </div>
      {!!cps.data?.length && (
        <section aria-label={t("audit.cp.recent")} className="mb-4 text-xs">
          <h2 className="mb-1 font-medium">{t("audit.cp.recent")}</h2>
          <ul className="flex flex-col gap-1">
            {cps.data.slice(0, 5).map((c) => (
              <li key={c.seq} className="flex flex-wrap items-center gap-2">
                <span>#{c.seq}</span><span className="font-mono">{short(c.hash)}</span><span>{formatDateTime(c.signed_at)}</span>
                <Button type="button" variant="outline" size="sm"
                  onClick={() => navigator.clipboard.writeText(c.token).then(() => toast.success(t("audit.cp.copied")), () => toast.error(t("error.action")))}>
                  {t("audit.cp.copy")}
                </Button>
              </li>
            ))}
          </ul>
        </section>
      )}
      <form className="mb-3 flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
        <FilterSelect id="a-role" label={t("audit.filterActor")} value={f.role ?? ""} onChange={(v) => set("role", v)}
          options={ROLES.map((r) => ({ value: r, label: r }))} any={t("audit.anyActor")} />
        <div className="flex flex-col gap-1">
          <Label htmlFor="a-action">{t("audit.filterAction")}</Label>
          <Input id="a-action" className="w-48" value={f.action ?? ""} onChange={(e) => set("action", e.target.value)} />
        </div>
        <FilterSelect id="a-entity" label={t("audit.filterEntity")} value={f.entity ?? ""} onChange={(v) => set("entity", v)}
          options={entities.map((r) => ({ value: r, label: r }))} any={t("audit.anyEntity")} />
        <div className="flex flex-col gap-1">
          <Label htmlFor="a-from">{t("audit.filterFrom")}</Label>
          <Input id="a-from" type="date" className="w-40" value={f.from ?? ""} onChange={(e) => set("from", e.target.value)} />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="a-to">{t("audit.filterTo")}</Label>
          <Input id="a-to" type="date" className="w-40" value={f.to ?? ""} onChange={(e) => set("to", e.target.value)} />
        </div>
        <Button type="button" variant="outline" size="sm" onClick={() => setF({})}>{t("filter.clear")}</Button>
      </form>
      <p className="mb-3 text-xs text-muted-foreground">{t("audit.filterNote")} {q.data && t("audit.total").replace("{n}", String(q.data.total))}</p>
      <DataTable columns={columns} caption={t("nav.audit")} data={rows} loading={q.isPending} onRetry={() => q.refetch()}
        error={q.isError ? t(q.error.status === 403 ? "error.forbidden" : "error.generic") : null}
        paging={q.data ? { total: q.data.total, limit: LIMIT, offset, onOffset: setOffset } : undefined}
        labels={{ empty: t("audit.empty"), error: t("error.generic"), retry: t("state.retry"), prev: t("table.prev"), next: t("table.next") }} />
      <ConfirmDialog open={askTamper} title={t("audit.tamperTitle")} body={t("audit.tamperBody")} confirmLabel={t("audit.tamperConfirm")}
        cancelLabel={t("dialog.cancel")} pending={busy} onConfirm={tamper} onClose={() => setAskTamper(false)} />
      <ConfirmDialog open={askTrunc} title={t("audit.truncTitle")} body={t("audit.truncBody")} confirmLabel={t("audit.truncConfirm")}
        cancelLabel={t("dialog.cancel")} pending={busy} onConfirm={truncate} onClose={() => setAskTrunc(false)} />
    </>
  );
}

export default function Page() {
  return (
    <RoleGuard roles={["AICTE_ADMIN"]}>
      <Audit />
    </RoleGuard>
  );
}
