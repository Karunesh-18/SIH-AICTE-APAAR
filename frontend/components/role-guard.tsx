"use client";
import type { ReactNode } from "react";
import Link from "next/link";
import { ShieldAlert } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { allowed } from "@/lib/guard";
import { homeFor, type Role } from "@/lib/nav";

/** UI convenience only: the server enforces the role on every route. */
export function RoleGuard({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const { user, t } = useAuth();
  if (!allowed(user?.role, roles)) {
    return (
      <div role="alert" className="flex max-w-md flex-col items-start gap-3 rounded-md border border-border p-6">
        <ShieldAlert aria-hidden className="size-6 text-muted-foreground" />
        <h1 className="text-lg font-semibold">{t("forbidden.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("error.forbidden")}</p>
        {user && <Link href={homeFor(user.role)} className="inline-flex min-h-11 items-center text-sm font-medium underline underline-offset-4">{t("forbidden.home")}</Link>}
      </div>
    );
  }
  return <>{children}</>;
}
