"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { QueryError } from "@/components/query-error";
import { RoleGuard } from "@/components/role-guard";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { diffVersions, parseParams } from "@/lib/rules";
import { formatDateTime } from "@/lib/status";
import type { RuleVersion } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";

const pretty = (v: unknown) => (typeof v === "string" ? v : JSON.stringify(v, null, 2)) ?? "";

function EditForm({ active, code, onSaved }: { active: RuleVersion; code: string; onSaved: () => void }) {
  const { t } = useAuth();
  const [text, setText] = useState(() => JSON.stringify(active.params, null, 2));
  const [enabled, setEnabled] = useState(active.enabled);
  const [hardStop, setHardStop] = useState(active.hard_stop);
  const [note, setNote] = useState("");
  const parsed = parseParams(text);
  const save = useMutation({
    mutationFn: () => api.put(`/admin/rules/${code}`, {
      params: parsed.ok ? parsed.value : undefined, enabled, hard_stop: hardStop, note: note.trim(),
    }),
    onSuccess: () => { setNote(""); toast.success(t("rules.saved")); onSaved(); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : t("error.generic")),
  });
  return (
    <form className="flex max-w-xl flex-col gap-4" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="params">{t("rules.params")}</Label>
        <Textarea id="params" rows={8} className="font-mono text-sm" value={text} onChange={(e) => setText(e.target.value)}
                  aria-invalid={!parsed.ok} aria-describedby="params-err" />
        <p id="params-err" role="alert" className="min-h-5 text-sm text-status-excess">{!parsed.ok && t(parsed.error)}</p>
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} /> {t("rules.enabled")}
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={hardStop} onChange={(e) => setHardStop(e.target.checked)} /> {t("rules.hardStop")}
      </label>
      <p className="text-sm text-muted-foreground">{t("rules.hardStopHint")}</p>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="note">{t("rules.note")}</Label>
        <Textarea id="note" rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
      </div>
      <div><Button type="submit" disabled={!parsed.ok || !note.trim() || save.isPending}>{t("rules.saveNew")}</Button></div>
    </form>
  );
}

function DiffView({ versions }: { versions: RuleVersion[] }) {
  const { t } = useAuth();
  const [from, setFrom] = useState<string>(String(versions[1]?.version_no ?? versions[0].version_no));
  const [to, setTo] = useState<string>(String(versions[0].version_no));
  const a = versions.find((v) => String(v.version_no) === from);
  const b = versions.find((v) => String(v.version_no) === to);
  const changes = a && b ? diffVersions(a, b) : [];
  const picker = (label: string, value: string, set: (v: string) => void) => (
    <div className="flex items-center gap-2">
      <Label>{label}</Label>
      <Select value={value} onValueChange={(v) => set(v as string)}>
        <SelectTrigger className="w-24" aria-label={label}><SelectValue /></SelectTrigger>
        <SelectContent>{versions.map((v) => <SelectItem key={v.id} value={String(v.version_no)}>v{v.version_no}</SelectItem>)}</SelectContent>
      </Select>
    </div>
  );
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-4">{picker(t("rules.from"), from, setFrom)}{picker(t("rules.to"), to, setTo)}</div>
      {changes.length === 0 ? <p className="text-sm">{t("rules.noDiff")}</p> : (
        <div className="grid gap-px overflow-hidden rounded-md border border-border bg-border text-sm md:grid-cols-2">
          <p className="bg-muted p-2 font-medium">v{from}</p><p className="bg-muted p-2 font-medium">v{to}</p>
          {changes.map((c) => (
            <div key={c.field} className="contents">
              <pre className="whitespace-pre-wrap bg-status-excess-bg p-2 font-mono text-xs"><b>{c.field}</b>{"\n"}{pretty(c.from)}</pre>
              <pre className="whitespace-pre-wrap bg-status-clear-bg p-2 font-mono text-xs"><b>{c.field}</b>{"\n"}{pretty(c.to)}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Rule() {
  const { code } = useParams<{ code: string }>();
  const { t } = useAuth();
  const qc = useQueryClient();
  const path = `/admin/rules/${code}/versions`;
  const q = useApiQuery<RuleVersion[]>(path);
  const [target, setTarget] = useState<RuleVersion | null>(null);
  const [note, setNote] = useState("");
  const refresh = () => qc.invalidateQueries({ queryKey: ["api"] });
  const revert = useMutation({
    mutationFn: (v: RuleVersion) => api.post(`/admin/rules/${code}/revert`, { to_version: v.version_no, note: note.trim() }),
    onSuccess: () => { setTarget(null); setNote(""); toast.success(t("rules.reverted")); refresh(); },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : t("error.generic")),
  });
  const versions = q.data;
  const active = versions?.find((v) => v.is_active);

  return (
    <>
      <PageHeader title={`${code} - ${t(`rule.${code}`)}`} actions={<Link className="text-sm underline" href="/admin/rules">{t("rules.back")}</Link>} />
      {q.isPending && <Skeleton className="h-40 w-full max-w-2xl" />}
      {q.isError && <QueryError error={q.error} onRetry={() => q.refetch()} />}
      {versions && active && (
        <Tabs defaultValue="versions">
          <TabsList>
            <TabsTrigger value="versions">{t("rules.versions")}</TabsTrigger>
            <TabsTrigger value="edit">{t("rules.edit")}</TabsTrigger>
            <TabsTrigger value="diff">{t("rules.diff")}</TabsTrigger>
          </TabsList>
          <TabsContent value="versions" className="pt-4">
            <ol className="flex flex-col gap-3">
              {versions.map((v) => (
                <li key={v.id} className="rounded-md border border-border p-4 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-medium tabular-nums">v{v.version_no} {v.is_active && <span className="ml-2 rounded bg-status-clear-bg px-1.5 py-0.5 text-xs text-status-clear">{t("rules.active")}</span>}</p>
                    {!v.is_active && <Button variant="outline" size="sm" onClick={() => setTarget(v)}>{t("rules.revert")}</Button>}
                  </div>
                  <p className="text-muted-foreground">{formatDateTime(v.created_at)} - {v.note ?? ""}</p>
                  <code className="mt-2 block font-mono text-xs">{JSON.stringify(v.params)}</code>
                </li>
              ))}
            </ol>
          </TabsContent>
          <TabsContent value="edit" className="pt-4"><EditForm key={active.id} active={active} code={code} onSaved={refresh} /></TabsContent>
          <TabsContent value="diff" className="pt-4"><DiffView versions={versions} /></TabsContent>
        </Tabs>
      )}
      <Dialog open={!!target} onOpenChange={(o) => { if (!o) { setTarget(null); setNote(""); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("rules.revertTitle")} v{target?.version_no}</DialogTitle>
            <DialogDescription>{t("rules.revertBody")}</DialogDescription>
          </DialogHeader>
          <Label htmlFor="rnote">{t("rules.note")}</Label>
          <Textarea id="rnote" rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
          <DialogFooter>
            <Button variant="outline" onClick={() => setTarget(null)}>{t("dialog.cancel")}</Button>
            <Button disabled={!note.trim() || revert.isPending} onClick={() => target && revert.mutate(target)}>{t("rules.revert")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default function Page() {
  return (
    <RoleGuard roles={["AICTE_ADMIN"]}>
      <Rule />
    </RoleGuard>
  );
}
