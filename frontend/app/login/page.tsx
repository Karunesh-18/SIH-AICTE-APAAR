"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LangSwitch } from "@/components/lang-switch";
import { SkipLink } from "@/components/skip-link";
import { ThemeToggle } from "@/components/theme-toggle";
import { BrandLockup, BrandMark } from "@/components/brand";
import { demoEnabled } from "@/lib/demo";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { homeFor } from "@/lib/nav";

const DEMO = [
  ["AICTE_ADMIN", "admin@demo.test"],
  ["AICTE_OFFICER", "officer@demo.test"],
  ["INSTITUTION_ADMIN", "inst-admin@demo.test"],
  ["INSTITUTION_STAFF", "staff@demo.test"],
  ["VERIFIER", "verifier@demo.test"],
] as const;
const DEMO_PASSWORD = "Demo@1234";

export default function LoginPage() {
  const { signIn, t } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const showDemo = demoEnabled();

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const me = await signIn(email, password);
      router.replace(homeFor(me.role));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("auth.networkError"));
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      <SkipLink />
      <aside className="brand-panel hidden flex-col justify-between gap-10 p-12 lg:flex">
        <BrandLockup tagline />
        <div className="flex max-w-md flex-col gap-4">
          <p className="t-eyebrow">APAAR</p>
          <p className="t-display">{t("brand.tagline")}</p>
          <p className="text-muted-foreground">{t("auth.panelBody")}</p>
        </div>
        <p className="text-xs text-muted-foreground">{t("app.notice")}</p>
      </aside>
      <main id="main" className="mx-auto flex w-full max-w-md flex-col justify-center gap-6 px-4 py-10 lg:max-w-lg lg:px-10">
        <div className="flex items-center justify-between gap-3">
          <h1 className="sr-only">{t("app.name")}</h1>
          <span aria-hidden className="flex items-center gap-2 lg:hidden">
            <BrandMark className="size-8" />
            <span className="t-section">{t("app.name")}</span>
          </span>
          <span className="hidden lg:block" />
          <span className="flex gap-2"><LangSwitch /><ThemeToggle /></span>
        </div>
        <form onSubmit={submit} className="rule-primary flex flex-col gap-4 pt-5" noValidate>
          <h2 className="t-title">{t("auth.title")}</h2>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="email">{t("auth.email")}</Label>
            <Input id="email" type="email" autoComplete="username" required value={email}
                   className="min-h-11" onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="password">{t("auth.password")}</Label>
            <Input id="password" type="password" autoComplete="current-password" required value={password}
                   className="min-h-11" onChange={(e) => setPassword(e.target.value)} />
          </div>
          {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
          <Button type="submit" size="lg" className="min-h-11" disabled={busy || !email || !password}>
            {busy ? t("auth.signingIn") : t("auth.submit")}
          </Button>
        </form>
        <Link href="/verifiers/register" className="inline-flex min-h-11 w-fit items-center text-sm underline underline-offset-4">{t("reg.link")}</Link>
        {showDemo && (
          <details className="rounded-md border border-dashed border-border p-3">
            <summary className="flex min-h-11 cursor-pointer items-center gap-2 text-sm font-medium">
              <span className="rounded-sm bg-muted px-1.5 py-0.5 text-xs font-semibold">{t("auth.demoOnly")}</span>
              {t("auth.demo")}
            </summary>
            <p className="mt-1 text-xs text-muted-foreground">{t("auth.demoHint")}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {DEMO.map(([role, mail]) => (
                <Button key={mail} type="button" variant="outline" size="sm" className="min-h-11"
                        onClick={() => { setEmail(mail); setPassword(DEMO_PASSWORD); }}>
                  {t(`role.${role}`)}
                </Button>
              ))}
            </div>
          </details>
        )}
        <p className="text-xs text-muted-foreground lg:hidden">{t("app.notice")}</p>
      </main>
    </div>
  );
}
