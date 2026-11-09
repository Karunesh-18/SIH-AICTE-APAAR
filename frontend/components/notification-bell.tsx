"use client";
import Link from "next/link";
import { Bell } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useApiQuery } from "@/lib/use-api";

export const BELL_POLL_MS = 30_000;

export function NotificationBell() {
  const { t } = useAuth();
  const q = useApiQuery<{ count: number }>("/notifications/unread-count", {
    refetchInterval: BELL_POLL_MS, refetchOnWindowFocus: true,
  });
  const n = q.data?.count ?? 0;
  return (
    <Link href="/notifications" className="relative inline-flex size-8 items-center justify-center rounded-md hover:bg-muted"
          aria-label={n > 0 ? `${t("notif.title")}: ${n} ${t("notif.unread")}` : t("notif.title")}>
      <Bell aria-hidden className="size-4" />
      {n > 0 && (
        <span aria-hidden className="absolute -top-0.5 -right-0.5 min-w-4 rounded-full bg-status-excess px-1 text-center text-[10px] leading-4 font-medium text-white tabular-nums">
          {n > 99 ? "99+" : n}
        </span>
      )}
    </Link>
  );
}
