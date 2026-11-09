"use client";
import Link from "next/link";
import { Timer } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { clockLabel } from "@/lib/dash";
import type { ClockState } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";

/** The clock endpoint is admin-only (not exposed to other roles), so the banner is admin-only too. */
export function ClockBanner() {
  const { user, t } = useAuth();
  const admin = user?.role === "AICTE_ADMIN";
  const q = useApiQuery<ClockState>(admin ? "/admin/clock" : null, { refetchInterval: 60_000 });
  const label = q.data ? clockLabel(q.data.offset_days) : null;
  if (!label) return null;
  return (
    <Link href="/admin/clock" role="status"
          className="mr-auto inline-flex items-center gap-1.5 rounded-md bg-status-alert-bg px-2.5 py-1 text-sm font-medium text-status-alert">
      <Timer aria-hidden className="size-4" />
      {t("clock.banner")}: {label} {t("clock.bannerDays")}
    </Link>
  );
}
