"use client";
import { useState, type FormEvent, type ReactNode } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Copy, KeyRound, Plus, TriangleAlert } from "lucide-react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { DataTable, type Col } from "@/components/data-table";
import { FilterSelect, selectClass } from "@/components/filter-select";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorKey } from "@/lib/guard";
import type { InstitutionRow, RegionRow, UserList, UserRow, UserSaved } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";
import { staffPath, userFormErrors, type UserForm } from "@/lib/users";

const ROLES = ["AICTE_ADMIN", "AICTE_OFFICER", "INSTITUTION_ADMIN", "INSTITUTION_STAFF"];
const LIMIT = 50;
const EMPTY: UserForm = { email: "", full_name: "", role: "AICTE_OFFICER", institution_id: "", regions: [], password: "" };
const isInst = (role: string) => role.startsWith("INSTITUTION");

type Mode = "admin" | "staff";
type Opts = { institutions: InstitutionRow[]; regions: RegionRow[] };

function Field({ id, label, error, children }: { id: string; label: string; error?: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      {children}
      {error && <p role="alert" className="text-sm text-status-excess">{error}</p>}
    </div>
  );
}

/** Create (u null) or edit (u set). Role, institution and regions are admin-only; staff can only rename and (de)activate. */
function UserDialog({ mode, u, opts, busy, onSubmit, onClose }: {
  mode: Mode; u: UserRow | null; opts: Opts; busy: boolean;
  onSubmit: (f: UserForm, active: boolean) => void; onClose: () => void;
}) {
  const { t } = useAuth();
  const [f, setF] = useState<UserForm>(
    u ? { email: u.email, full_name: u.full_name, role: u.role, institution_id: u.institution_id ?? "", regions: u.regions, password: "" } : EMPTY,
  );
  const [active, setActive] = useState(u?.is_active ?? true);
  const [errs, setErrs] = useState<Record<string, string>>({});
  const set = <K extends keyof UserForm>(k: K, v: UserForm[K]) => setF((p) => ({ ...p, [k]: v }));
  const err = (k: string) => (errs[k] ? t(errs[k]) : undefined);
  const inst = isInst(f.role);

  function submit(ev: FormEvent) {
    ev.preventDefault();
    const found = userFormErrors({ ...f, email: u ? "ok@ok.test" : f.email }, mode);
    setErrs(found);
    if (Object.keys(found).length === 0) onSubmit(f, active);
  }

  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent>
        <form onSubmit={submit} noValidate className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>{u ? t("users.editTitle") : t("users.createTitle")}</DialogTitle>
            <DialogDescription>{u ? u.email : t("users.createHint")}</DialogDescription>
          </DialogHeader>
          {!u && (
            <Field id="u-email" label={t("auth.email")} error={err("email")}>
              <Input id="u-email" type="email" autoComplete="off" value={f.email} aria-invalid={!!errs.email}
                     onChange={(e) => set("email", e.target.value)} />
            </Field>
          )}
          <Field id="u-name" label={t("users.name")} error={err("full_name")}>
            <Input id="u-name" value={f.full_name} aria-invalid={!!errs.full_name} onChange={(e) => set("full_name", e.target.value)} />
          </Field>
          {mode === "admin" && (
            <>
              <Field id="u-role" label={t("users.role")}>
                <select id="u-role" className={selectClass} value={f.role} onChange={(e) => set("role", e.target.value)}>
                  {ROLES.map((r) => <option key={r} value={r}>{t(`role.${r}`)}</option>)}
                </select>
              </Field>
              {inst ? (
                <Field id="u-inst" label={t("users.institution")} error={err("institution_id")}>
                  <select id="u-inst" className={selectClass} value={f.institution_id} aria-invalid={!!errs.institution_id}
                          onChange={(e) => set("institution_id", e.target.value)}>
                    <option value="">{t("users.choose")}</option>
                    {opts.institutions.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
                  </select>
                </Field>
              ) : (
                opts.regions.length > 0 && (
                  <fieldset className="flex flex-col gap-1.5">
                    <legend className="text-sm font-medium">{t("users.regions")}</legend>
                    <div className="flex flex-wrap gap-x-4 gap-y-1">
                      {opts.regions.map((r) => (
                        <label key={r.id} className="flex min-h-8 items-center gap-2 text-sm">
                          <input type="checkbox" className="size-4" checked={f.regions.includes(r.code)}
                                 onChange={(e) => set("regions", e.target.checked ? [...f.regions, r.code] : f.regions.filter((c) => c !== r.code))} />
                          {r.name}
                        </label>
                      ))}
                    </div>
                  </fieldset>
                )
              )}
            </>
          )}
          {!u && (
            <Field id="u-pw" label={t("users.password")} error={err("password")}>
              <Input id="u-pw" type="password" autoComplete="new-password" value={f.password} aria-describedby="u-pw-hint"
                     aria-invalid={!!errs.password} onChange={(e) => set("password", e.target.value)} />
              <p id="u-pw-hint" className="text-xs text-muted-foreground">{t("users.passwordHint")}</p>
            </Field>
          )}
          {u && (
            <label className="flex min-h-8 items-center gap-2 text-sm">
              <input type="checkbox" className="size-4" checked={active} onChange={(e) => setActive(e.target.checked)} />
              {t("users.active")}
            </label>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>{t("dialog.cancel")}</Button>
            <Button type="submit" disabled={busy}>{u ? t("users.save") : t("users.create")}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function UsersManager({ mode }: { mode: Mode }) {
  const { t, user } = useAuth();
  const qc = useQueryClient();
  const inst = user?.institution_id ?? null;
  const [role, setRole] = useState("");
  const [active, setActive] = useState("");
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);
  const [editing, setEditing] = useState<UserRow | "new" | null>(null);
  const [deactivating, setDeactivating] = useState<UserRow | null>(null);
  const [resetting, setResetting] = useState<UserRow | null>(null);
  const [shown, setShown] = useState<{ email: string; pw: string } | null>(null);

  const params = new URLSearchParams({ limit: String(LIMIT), offset: String(offset) });
  if (active) params.set("active", active);
  if (mode === "admin") {
    if (role) params.set("role", role);
    if (q.trim()) params.set("q", q.trim());
  }
  const base = mode === "admin" ? "/admin/users" : inst ? staffPath(inst) : null;
  const list = useApiQuery<UserList>(base ? `${base}?${params}` : null);
  const insts = useApiQuery<InstitutionRow[]>("/institutions", { enabled: mode === "admin" });
  const regions = useApiQuery<RegionRow[]>("/regions", { enabled: mode === "admin" });
  const opts: Opts = { institutions: insts.data ?? [], regions: regions.data ?? [] };

  const one = (id: string, action?: string) =>
    mode === "admin" ? `/admin/users/${id}${action ? `/${action}` : ""}` : staffPath(inst as string, id, action);
  const refresh = () => qc.invalidateQueries({ queryKey: ["api"] });
  const fail = (e: unknown) =>
    toast.error(e instanceof ApiError && e.status !== 403 && e.status < 500 ? e.message : t(errorKey(e)));

  const save = useMutation({
    mutationFn: async ({ f, on }: { f: UserForm; on: boolean }) => {
      const name = f.full_name.trim();
      const scope = isInst(f.role) ? { institution_id: f.institution_id, regions: [] } : { institution_id: null, regions: f.regions };
      if (editing === "new") {
        const body = mode === "admin"
          ? { email: f.email.trim(), full_name: name, role: f.role, ...scope, password: f.password || undefined }
          : { email: f.email.trim(), full_name: name, password: f.password || undefined };
        return api.post<UserSaved>(base as string, body);
      }
      const body = mode === "admin" ? { full_name: name, role: f.role, is_active: on, ...scope } : { full_name: name, is_active: on };
      return api.patch<UserRow>(one((editing as UserRow).id), body);
    },
    onSuccess: (r) => {
      const created = editing === "new";
      setEditing(null);
      refresh();
      toast.success(t(created ? "users.created" : "users.saved"));
      const temp = (r as UserSaved).temporary_password;
      if (created && temp) setShown({ email: (r as UserSaved).user.email, pw: temp });
    },
    onError: fail,
  });
  const deactivate = useMutation({
    mutationFn: (u: UserRow) => (mode === "admin" ? api.patch(one(u.id), { is_active: false }) : api.del(one(u.id))),
    onSuccess: () => { setDeactivating(null); refresh(); toast.success(t("users.deactivated")); },
    onError: (e) => { setDeactivating(null); fail(e); },
  });
  const reset = useMutation({
    mutationFn: (u: UserRow) => api.post<UserSaved>(one(u.id, "reset-password")),
    onSuccess: (r) => { setResetting(null); setShown({ email: r.user.email, pw: r.temporary_password ?? "" }); },
    onError: (e) => { setResetting(null); fail(e); },
  });

  const columns: Col<UserRow>[] = [
    { accessorKey: "full_name", header: t("users.name") },
    { accessorKey: "email", header: t("auth.email") },
    ...(mode === "admin"
      ? [
          { id: "role", header: t("users.role"), accessorFn: (r: UserRow) => t(`role.${r.role}`) } as Col<UserRow>,
          { id: "scope", header: t("users.scope"), enableSorting: false,
            cell: (c) => c.row.original.institution_name ?? (c.row.original.regions.join(", ") || t("users.allRegions")) } as Col<UserRow>,
        ]
      : []),
    { id: "state", header: t("record.status"), accessorFn: (r: UserRow) => (r.is_active ? 1 : 0),
      cell: (c) => (c.row.original.is_active ? t("users.stateActive") : t("users.stateInactive")) },
    { id: "act", header: t("users.actions"), enableSorting: false,
      cell: (c) => {
        const r = c.row.original;
        return (
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => setEditing(r)}>{t("users.edit")}</Button>
            <Button variant="outline" size="sm" onClick={() => setResetting(r)}><KeyRound data-icon="inline-start" /> {t("users.reset")}</Button>
            {r.is_active && r.id !== user?.id && <Button variant="outline" size="sm" onClick={() => setDeactivating(r)}>{t("users.deactivate")}</Button>}
          </div>
        );
      } },
  ];

  const title = t(mode === "admin" ? "nav.users" : "nav.staff");
  return (
    <>
      <PageHeader title={title} description={t(mode === "admin" ? "users.intro" : "users.staffIntro")}
                  actions={<Button onClick={() => setEditing("new")}><Plus data-icon="inline-start" /> {t("users.new")}</Button>} />
      <div className="mb-4 flex flex-wrap items-end gap-3">
        {mode === "admin" && (
          <>
            <FilterSelect id="f-role" label={t("users.role")} value={role} any={t("filter.any")}
                          onChange={(v) => { setRole(v); setOffset(0); }} options={ROLES.map((r) => ({ value: r, label: t(`role.${r}`) }))} />
            <div className="flex flex-col gap-1">
              <Label htmlFor="f-q">{t("users.search")}</Label>
              <Input id="f-q" type="search" className="h-8 w-56" value={q} onChange={(e) => { setQ(e.target.value); setOffset(0); }} />
            </div>
          </>
        )}
        <FilterSelect id="f-active" label={t("record.status")} value={active} any={t("filter.any")}
                      onChange={(v) => { setActive(v); setOffset(0); }}
                      options={[{ value: "true", label: t("users.stateActive") }, { value: "false", label: t("users.stateInactive") }]} />
      </div>
      <DataTable columns={columns} data={list.data?.items ?? []} caption={title} loading={list.isPending && !!base}
                 error={list.isError ? t(errorKey(list.error)) : null} onRetry={() => list.refetch()}
                 paging={list.data ? { total: list.data.total, limit: LIMIT, offset, onOffset: setOffset } : undefined}
                 labels={{ empty: t("users.empty"), error: t("error.generic"), retry: t("state.retry"), prev: t("table.prev"), next: t("table.next") }} />

      {editing && (
        <UserDialog mode={mode} u={editing === "new" ? null : editing} opts={opts} busy={save.isPending}
                    onSubmit={(f, on) => save.mutate({ f, on })} onClose={() => setEditing(null)} />
      )}
      <ConfirmDialog open={!!deactivating} title={t("users.deactivateTitle")} body={`${deactivating?.full_name ?? ""}: ${t("users.deactivateBody")}`}
                     confirmLabel={t("users.deactivate")} cancelLabel={t("dialog.cancel")} pending={deactivate.isPending}
                     onConfirm={() => deactivating && deactivate.mutate(deactivating)} onClose={() => setDeactivating(null)} />
      <ConfirmDialog open={!!resetting} title={t("users.resetTitle")} body={`${resetting?.full_name ?? ""}: ${t("users.resetBody")}`}
                     confirmLabel={t("users.reset")} cancelLabel={t("dialog.cancel")} pending={reset.isPending}
                     onConfirm={() => resetting && reset.mutate(resetting)} onClose={() => setResetting(null)} />
      <Dialog open={!!shown} onOpenChange={(o) => { if (!o) setShown(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("users.tempTitle")}</DialogTitle>
            <DialogDescription className="flex items-start gap-2 text-status-alert">
              <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0" /> {t("users.tempOnce")}
            </DialogDescription>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">{shown?.email}</p>
          <code className="block break-all rounded-md bg-muted p-3 font-mono text-sm">{shown?.pw}</code>
          <DialogFooter>
            <Button variant="outline" onClick={() => navigator.clipboard.writeText(shown?.pw ?? "").then(
              () => toast.success(t("users.copied")), () => toast.error(t("error.generic")))}>
              <Copy data-icon="inline-start" /> {t("users.copy")}
            </Button>
            <Button onClick={() => setShown(null)}>{t("users.done")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
