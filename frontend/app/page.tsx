"use client";
import Link from "next/link";
import { ArrowRight, ClipboardCheck, FileUp, ListChecks, QrCode } from "lucide-react";
import { LangSwitch } from "@/components/lang-switch";
import { SkipLink } from "@/components/skip-link";
import { ToneBadge } from "@/components/status-badge";
import { ThemeToggle } from "@/components/theme-toggle";
import { buttonVariants } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";
import { homeFor } from "@/lib/nav";
import { institutionState } from "@/lib/status";

const STEPS = [
  { key: "upload", Icon: FileUp },
  { key: "checks", Icon: ListChecks },
  { key: "review", Icon: ClipboardCheck },
  { key: "verify", Icon: QrCode },
] as const;
const STATES = ["Clear", "Alert", "Excess"] as const;

/** One fixed-size SVG: four waymarks on a line. Draws once; static when motion is reduced. */
function Waymark() {
  return (
    <svg viewBox="0 0 320 120" width="320" height="120" aria-hidden className="h-auto w-full max-w-xs text-primary">
      <path d="M20 90 C 90 90, 80 30, 160 30 S 230 90, 300 40" fill="none" stroke="currentColor" strokeWidth="2"
            strokeLinecap="round" pathLength={1} className="waymark-line" />
      {[[20, 90], [100, 52], [200, 52], [300, 40]].map(([x, y]) => (
        <circle key={x} cx={x} cy={y} r="6" className="fill-background stroke-current" strokeWidth="2" />
      ))}
    </svg>
  );
}

const btn = (v: "default" | "outline") => buttonVariants({ variant: v, size: "lg" }) + " min-h-11";

export default function Home() {
  const { user, t } = useAuth();
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-16 px-4 py-6 sm:px-6">
      <SkipLink />
      <header className="flex flex-wrap items-center justify-between gap-3">
        <p className="font-semibold">{t("app.name")}</p>
        <div className="flex flex-wrap items-center gap-2">
          <LangSwitch />
          <ThemeToggle />
          {user ? (
            <Link href={homeFor(user.role)} className={btn("default")}>{t("landing.open")}</Link>
          ) : (
            <Link href="/login" className={btn("outline")}>{t("common.signIn")}</Link>
          )}
        </div>
      </header>

      <main id="main" className="flex flex-col gap-20">
        <section className="grid items-center gap-8 md:grid-cols-[1.4fr_1fr]">
          <div className="flex flex-col gap-5">
            <h1 className="text-3xl font-semibold tracking-tight text-balance sm:text-4xl">{t("landing.title")}</h1>
            <p className="max-w-prose text-lg text-muted-foreground">{t("landing.lead")}</p>
            <div className="flex flex-wrap gap-3">
              {user ? (
                <Link href={homeFor(user.role)} className={btn("default")}>{t("landing.open")} <ArrowRight aria-hidden className="size-4" /></Link>
              ) : (
                <Link href="/login" className={btn("default")}>{t("common.signIn")} <ArrowRight aria-hidden className="size-4" /></Link>
              )}
              <Link href="/verify" className={btn("outline")}>{t("landing.verifyCta")}</Link>
            </div>
          </div>
          <div className="flex justify-center md:justify-end"><Waymark /></div>
        </section>

        <section aria-labelledby="flow-h" className="flex flex-col gap-6">
          <h2 id="flow-h" className="text-xl font-semibold">{t("landing.flowTitle")}</h2>
          <ol className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map(({ key, Icon }, i) => (
              <li key={key} className="flex flex-col gap-2 border-t-2 border-primary pt-3">
                <span className="flex items-center gap-2 text-sm text-muted-foreground tabular">
                  <Icon aria-hidden className="size-4 text-primary" /> {i + 1}
                </span>
                <h3 className="font-medium">{t(`landing.step.${key}`)}</h3>
                <p className="text-sm text-muted-foreground">{t(`landing.step.${key}.body`)}</p>
              </li>
            ))}
          </ol>
        </section>

        <section aria-labelledby="states-h" className="flex flex-col gap-6">
          <div>
            <h2 id="states-h" className="text-xl font-semibold">{t("landing.statesTitle")}</h2>
            <p className="mt-1 max-w-prose text-sm text-muted-foreground">{t("landing.statesLead")}</p>
          </div>
          <ul className="grid gap-4 sm:grid-cols-3">
            {STATES.map((s) => (
              <li key={s} className="flex flex-col items-start gap-2 rounded-md border border-border p-4">
                <ToneBadge meta={institutionState(s)} label={t(`state.${s}`)} />
                <p className="text-sm">{t(`landing.state.${s}`)}</p>
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="adv-h" className="rounded-md border border-border bg-muted/50 p-6">
          <h2 id="adv-h" className="text-xl font-semibold">{t("landing.advisoryTitle")}</h2>
          <p className="mt-2 max-w-prose">{t("landing.advisoryBody")}</p>
        </section>

        <section aria-labelledby="paths-h" className="flex flex-col gap-6">
          <h2 id="paths-h" className="text-xl font-semibold">{t("landing.pathsTitle")}</h2>
          <ul className="grid gap-4 md:grid-cols-3">
            {([
              ["/login", "signin"],
              ["/verify", "verify"],
              ["/verifiers/register", "register"],
            ] as const).map(([href, k]) => (
              <li key={k} className="flex flex-col gap-2 rounded-md border border-border p-4">
                <h3 className="font-medium">{t(`landing.path.${k}`)}</h3>
                <p className="flex-1 text-sm text-muted-foreground">{t(`landing.path.${k}.body`)}</p>
                <Link href={href} className="inline-flex min-h-11 items-center gap-1 text-sm font-medium underline underline-offset-4">
                  {t(`landing.path.${k}.cta`)} <ArrowRight aria-hidden className="size-4" />
                </Link>
              </li>
            ))}
          </ul>
        </section>
      </main>

      <footer className="mt-auto border-t border-border pt-4 text-sm text-muted-foreground">
        <p>{t("app.notice")}</p>
        <p className="mt-1">{t("landing.team")}</p>
      </footer>
    </div>
  );
}
