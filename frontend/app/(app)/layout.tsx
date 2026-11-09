"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Suspense, useEffect, type ReactNode } from "react";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { NotificationBell } from "@/components/notification-bell";
import { LangSwitch } from "@/components/lang-switch";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/lib/auth";
import { navFor } from "@/lib/nav";
import { BrandLockup } from "@/components/brand";
import { ClockBanner } from "@/components/clock-banner";

function Shell({ children }: { children: ReactNode }) {
  const { user, loading, signOut, t } = useAuth();
  const router = useRouter();
  const path = usePathname();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (!user) return <main className="p-8 text-muted-foreground">{t("state.loading")}</main>;

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded-md focus:bg-background focus:px-3 focus:py-2 focus:text-sm focus:ring-2 focus:ring-ring">{t("a11y.skip")}</a>
      <aside className="flex flex-col gap-4 border-b border-sidebar-border bg-sidebar p-4 md:w-64 md:border-r md:border-b-0">
        <BrandLockup />
        <p className="text-xs text-muted-foreground md:hidden">{t("app.notice")}</p>
        <nav aria-label={t("a11y.primaryNav")} className="flex flex-row gap-1 overflow-x-auto text-sm md:flex-1 md:flex-col">
          {navFor(user.role).map((n) => {
            const active = path === n.href || path.startsWith(n.href + "/");
            return (
              <Link key={n.href} href={n.href} aria-current={active ? "page" : undefined}
                    className={`flex min-h-11 items-center rounded-md border-b-[3px] px-3 py-2 whitespace-nowrap md:min-h-11 md:border-b-0 md:border-s-[3px] ${
                      active
                        ? "border-primary bg-sidebar-accent font-semibold text-sidebar-accent-foreground"
                        : "border-transparent text-sidebar-foreground hover:bg-sidebar-accent/60"
                    }`}>
                {t(n.key)}
              </Link>
            );
          })}
        </nav>
        <p className="hidden text-xs text-muted-foreground md:block">{t("app.notice")}</p>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header role="banner" className="flex flex-wrap items-center justify-end gap-3 border-b border-border px-6 py-3">
          <ClockBanner />
          <span className="text-sm text-muted-foreground">{user.full_name}</span>
          <NotificationBell />
          <LangSwitch />
          <ThemeToggle />
          <Button variant="outline" size="sm" onClick={signOut}>
            <LogOut data-icon="inline-start" /> {t("auth.signOut")}
          </Button>
        </header>
        <main id="main" tabIndex={-1} className="flex-1 p-6 focus:outline-none">{children}</main>
      </div>
    </div>
  );
}

// usePathname/useParams suspend on dynamic routes under Cache Components, so the shell needs a boundary.
export default function AppShell({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<main className="p-8 text-muted-foreground">Loading...</main>}>
      <Shell>{children}</Shell>
    </Suspense>
  );
}
