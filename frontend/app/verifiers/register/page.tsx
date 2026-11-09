"use client";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { CheckCircle2 } from "lucide-react";
import { CheckGroup, FieldError, PublicFrame } from "@/components/consent-parts";
import { selectClass } from "@/components/filter-select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ORG_TYPES, PURPOSES, validateRegister } from "@/lib/consent";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const EMPTY = { org_name: "", org_type: "", contact: "", email: "", password: "", purposes: [] as string[] };

export default function Page() {
  const { t } = useAuth();
  const [f, setF] = useState(EMPTY);
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [fail, setFail] = useState<string | null>(null);
  const set = <K extends keyof typeof EMPTY>(k: K, v: (typeof EMPTY)[K]) => setF((p) => ({ ...p, [k]: v }));
  const e = (k: string) => (errs[k] ? t(errs[k]) : undefined);

  async function submit(ev: FormEvent) {
    ev.preventDefault();
    const found = validateRegister(f);
    setErrs(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    setFail(null);
    try {
      const res = await fetch(`${BASE}/verifiers/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          org_name: f.org_name.trim(), org_type: f.org_type, contact: f.contact.trim(), email: f.email.trim(),
          password: f.password, requested_purposes: f.purposes,
        }),
      });
      if (!res.ok) throw new ApiError(res.status, res.statusText);
      setDone(true); // the same screen whatever the address was: the server does not say if it exists
    } catch (err) {
      setFail(err instanceof ApiError && err.status === 429 ? t("reg.limited") : t("reg.error"));
    }
    setBusy(false);
  }

  return (
    <PublicFrame>
      <div>
        <h1 className="text-xl font-semibold">{t("reg.title")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("reg.intro")}</p>
      </div>
      <p className="rounded-md border border-border p-3 text-sm">{t("reg.approval")}</p>
      {done ? (
        <div role="status" className="flex flex-col gap-3 rounded-md border border-status-clear/40 bg-status-clear-bg p-4">
          <p className="flex items-center gap-2 font-semibold text-status-clear"><CheckCircle2 aria-hidden className="size-5" />{t("reg.doneTitle")}</p>
          <p className="text-sm">{t("reg.done")}</p>
          <Link href="/login" className="w-fit text-sm underline underline-offset-4">{t("reg.haveAccount")}</Link>
        </div>
      ) : (
        <form onSubmit={submit} noValidate className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="r-org">{t("reg.org")}</Label>
            <Input id="r-org" autoComplete="organization" value={f.org_name} aria-invalid={!!errs.org_name} onChange={(x) => set("org_name", x.target.value)} />
            <FieldError msg={e("org_name")} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="r-type">{t("reg.type")}</Label>
            <select id="r-type" className={selectClass} value={f.org_type} aria-invalid={!!errs.org_type} onChange={(x) => set("org_type", x.target.value)}>
              <option value="">{t("reg.typeChoose")}</option>
              {ORG_TYPES.map((o) => <option key={o} value={o}>{t(`orgType.${o}`)}</option>)}
            </select>
            <FieldError msg={e("org_type")} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="r-contact">{t("reg.contact")}</Label>
            <Input id="r-contact" autoComplete="name" value={f.contact} aria-invalid={!!errs.contact} onChange={(x) => set("contact", x.target.value)} />
            <FieldError msg={e("contact")} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="r-email">{t("reg.email")}</Label>
            <Input id="r-email" type="email" autoComplete="email" value={f.email} aria-invalid={!!errs.email} onChange={(x) => set("email", x.target.value)} />
            <FieldError msg={e("email")} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="r-pw">{t("reg.password")}</Label>
            <Input id="r-pw" type="password" autoComplete="new-password" value={f.password} aria-invalid={!!errs.password} aria-describedby="r-pw-h" onChange={(x) => set("password", x.target.value)} />
            <p id="r-pw-h" className="text-xs text-muted-foreground">{t("reg.passwordHint")}</p>
            <FieldError msg={e("password")} />
          </div>
          <CheckGroup legend={t("reg.purposes")} value={f.purposes} onChange={(v) => set("purposes", v)} error={e("purposes")}
            options={PURPOSES.map((p) => ({ value: p, label: t(`purpose.${p}`), desc: t(`purpose.${p}.desc`) }))} />
          {fail && <p role="alert" className="text-sm text-status-excess">{fail}</p>}
          <Button type="submit" disabled={busy} className="w-fit">{busy ? t("reg.sending") : t("reg.submit")}</Button>
        </form>
      )}
    </PublicFrame>
  );
}
