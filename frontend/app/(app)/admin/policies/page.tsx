"use client";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { CheckGroup } from "@/components/consent-parts";
import { PageHeader } from "@/components/page-header";
import { QueryError } from "@/components/query-error";
import { RoleGuard } from "@/components/role-guard";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { policyHistory } from "@/lib/audit";
import { useAuth } from "@/lib/auth";
import { fieldLabelKey, validatePolicyNote } from "@/lib/consent";
import { formatDateTime } from "@/lib/status";
import type { AuditRow, PolicyAdmin, Policies } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";

const PATH = "/admin/policies";
const AUDIT = "/admin/audit?limit=500";

function Editor({ policy, all, onClose }: { policy: PolicyAdmin; all: string[]; onClose: () => void }) {
  const { t } = useAuth();
  const qc = useQueryClient();
  const [fields, setFields] = useState<string[]>(policy.allowed_fields);
  const [note, setNote] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function save() {
    const e = validatePolicyNote(note);
    setErr(e);
    if (e) return;
    setBusy(true);
    try {
      await api.put(`${PATH}/${policy.purpose}`, { allowed_fields: fields, note: note.trim() });
      toast.success(t("pol.saved"));
      qc.invalidateQueries({ queryKey: ["api"] });
      onClose();
    } catch {
      toast.error(t("error.action"));
      setBusy(false);
    }
  }

  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("pol.editTitle")}: {t(`purpose.${policy.purpose}`)}</DialogTitle>
          <DialogDescription>{t(`purpose.${policy.purpose}.desc`)}</DialogDescription>
        </DialogHeader>
        <CheckGroup legend={t("vr.fields")} value={fields} onChange={setFields} options={all.map((f) => ({ value: f, label: t(fieldLabelKey(f)) }))} />
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="pol-note">{t("pol.note")}</Label>
          <Textarea id="pol-note" rows={3} value={note} aria-invalid={!!err} onChange={(e) => { setNote(e.target.value); setErr(null); }} />
          {err && <p role="alert" className="text-sm text-status-excess">{t(err)}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>{t("dialog.cancel")}</Button>
          <Button disabled={busy} onClick={save}>{t("pol.save")}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Policies_() {
  const { t } = useAuth();
  const q = useApiQuery<Policies<PolicyAdmin>>(PATH);
  const audit = useApiQuery<{ items: AuditRow[] }>(AUDIT);
  const [editing, setEditing] = useState<PolicyAdmin | null>(null);
  const fieldsText = (fs: string[]) => fs.map((f) => t(fieldLabelKey(f))).join(", ") || t("pol.noFields");

  return (
    <>
      <PageHeader title={t("pol.title")} description={t("pol.intro")} />
      {q.isPending && <Skeleton className="h-40 w-full max-w-2xl" />}
      {q.isError && <QueryError error={q.error} onRetry={() => q.refetch()} />}
      {q.data && (
        <ul className="flex max-w-2xl flex-col gap-4">
          {q.data.items.map((p) => {
            const hist = audit.data ? policyHistory(audit.data.items, p.purpose) : [];
            return (
              <li key={p.purpose} className="flex flex-col gap-2 rounded-md border border-border p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h2 className="font-semibold">{t(`purpose.${p.purpose}`)}</h2>
                    <p className="text-sm text-muted-foreground">{t(`purpose.${p.purpose}.desc`)}</p>
                  </div>
                  <Button size="sm" variant="outline" onClick={() => setEditing(p)}>{t("pol.edit")}</Button>
                </div>
                <p className="text-sm">{fieldsText(p.allowed_fields)}</p>
                <p className="text-xs text-muted-foreground">
                  {t("pol.version")} {p.version} · {t("pol.updated")} {formatDateTime(p.updated_at)}{p.note ? ` · ${p.note}` : ""}
                </p>
                <details className="text-sm">
                  <summary className="cursor-pointer">{t("pol.history")}</summary>
                  {hist.length === 0 ? <p className="mt-1 text-muted-foreground">{t("pol.historyEmpty")}</p> : (
                    <ul className="mt-2 flex flex-col gap-1">
                      {hist.map((h) => (
                        <li key={h.id}>
                          {t("pol.historyRow").replace("{v}", String(h.version)).replace("{fields}", fieldsText(h.allowed_fields))}
                          <span className="text-muted-foreground"> · {formatDateTime(h.at)}{h.note ? ` · ${h.note}` : ""}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </details>
              </li>
            );
          })}
        </ul>
      )}
      {editing && q.data && <Editor policy={editing} all={q.data.fields} onClose={() => setEditing(null)} />}
    </>
  );
}

export default function Page() {
  return (
    <RoleGuard roles={["AICTE_ADMIN"]}>
      <Policies_ />
    </RoleGuard>
  );
}
