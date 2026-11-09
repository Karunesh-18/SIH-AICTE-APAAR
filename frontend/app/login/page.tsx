"use client";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ThemeToggle } from "@/components/theme-toggle";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { t } from "@/lib/i18n";
import { homeFor } from "@/lib/nav";

const DEMO = [
  ["AICTE admin", "admin@demo.test"],
  ["AICTE officer", "officer@demo.test"],
  ["Institution admin", "inst-admin@demo.test"],
  ["Institution staff", "staff@demo.test"],
  ["Verifier", "verifier@demo.test"],
] as const;
const DEMO_PASSWORD = "Demo@1234";

export default function LoginPage() {
  const { signIn } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const showDemo = process.env.NEXT_PUBLIC_DEMO !== "0";

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const me = await signIn(email, password);
      router.replace(homeFor(me.role));
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not reach the server. Check that the API is running.",
      );
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-md flex-col justify-center gap-6 px-4 py-10">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">{t("en", "app.name")}</h1>
        <ThemeToggle />
      </div>
      <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
        <h2 className="text-base font-medium">{t("en", "auth.title")}</h2>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="email">{t("en", "auth.email")}</Label>
          <Input id="email" type="email" autoComplete="username" required value={email}
                 onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="password">{t("en", "auth.password")}</Label>
          <Input id="password" type="password" autoComplete="current-password" required value={password}
                 onChange={(e) => setPassword(e.target.value)} />
        </div>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <Button type="submit" disabled={busy || !email || !password}>
          {busy ? t("en", "auth.signingIn") : t("en", "auth.submit")}
        </Button>
      </form>
      {showDemo && (
        <section aria-labelledby="demo" className="border-t border-border pt-4">
          <h2 id="demo" className="text-sm font-medium">
            {t("en", "auth.demo")}
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">{t("en", "auth.demoHint")}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {DEMO.map(([label, mail]) => (
              <Button key={mail} type="button" variant="outline" size="sm"
                      onClick={() => { setEmail(mail); setPassword(DEMO_PASSWORD); }}>
                {label}
              </Button>
            ))}
          </div>
        </section>
      )}
      <p className="text-xs text-muted-foreground">{t("en", "app.notice")}</p>
    </main>
  );
}
