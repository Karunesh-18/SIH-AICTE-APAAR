"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Suspense, useEffect, type ReactNode } from "react";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { NotificationBell } from "@/components/notification-bell";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/lib/auth";
import { navFor } from "@/lib/nav";
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
      <aside className="flex flex-col gap-4 border-b border-sidebar-border bg-sidebar p-4 md:w-60 md:border-r md:border-b-0">
        <p className="font-semibold">{t("app.name")}</p>
        <nav aria-label="Primary" className="flex flex-row gap-1 overflow-x-auto text-sm md:flex-1 md:flex-col">
          {navFor(user.role).map((n) => {
            const active = path === n.href || path.startsWith(n.href + "/");
            return (
              <Link key={n.href} href={n.href} aria-current={active ? "page" : undefined}
                    className={`rounded-md px-3 py-2 whitespace-nowrap ${
                      active
                        ? "bg-sidebar-accent font-medium text-sidebar-accent-foreground"
                        : "text-sidebar-foreground hover:bg-sidebar-accent/60"
                    }`}>
                {t(n.key)}
              </Link>
            );
          })}
        </nav>
        <p className="hidden text-xs text-muted-foreground md:block">{t("app.notice")}</p>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center justify-end gap-3 border-b border-border px-6 py-3">
          <ClockBanner />
          <span className="text-sm text-muted-foreground">{user.full_name}</span>
          <NotificationBell />
          <ThemeToggle />
          <Button variant="outline" size="sm" onClick={signOut}>
            <LogOut data-icon="inline-start" /> {t("auth.signOut")}
          </Button>
        </header>
        <main className="flex-1 p-6">{children}</main>
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
