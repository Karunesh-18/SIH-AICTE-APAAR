"use client";
import type { ReactNode } from "react";
import { ShieldAlert } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { allowed } from "@/lib/guard";
import type { Role } from "@/lib/nav";

/** UI convenience only: the server enforces the role on every route. */
export function RoleGuard({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const { user, t } = useAuth();
  if (!allowed(user?.role, roles)) {
    return (
      <div role="alert" className="flex items-center gap-2 rounded-md border border-border p-6 text-sm">
        <ShieldAlert aria-hidden className="size-5 text-muted-foreground" />
        {t("error.forbidden")}
      </div>
    );
  }
  return <>{children}</>;
}
