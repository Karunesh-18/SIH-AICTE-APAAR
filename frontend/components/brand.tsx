"use client";
import { useAuth } from "@/lib/auth";

/** Original Waymark mark: a route through three waypoints in a verdigris square. Not an official emblem. */
export function BrandMark({ className = "size-9" }: { className?: string }) {
  return (
    <svg viewBox="0 0 36 36" aria-hidden className={`shrink-0 ${className}`}>
      <rect width="36" height="36" rx="6" className="fill-primary" />
      <path d="M7 27 C 13 27, 12 12, 18 12 S 24 24, 29 10" fill="none" strokeWidth="2.5" strokeLinecap="round"
            className="stroke-primary-foreground" />
      {[[7, 27], [18, 12], [29, 10]].map(([x, y]) => (
        <circle key={x} cx={x} cy={y} r="3" strokeWidth="2" className="fill-primary stroke-primary-foreground" />
      ))}
    </svg>
  );
}

/** Mark plus wordmark; the tagline is optional so the shell header stays compact. */
export function BrandLockup({ tagline = false, className = "" }: { tagline?: boolean; className?: string }) {
  const { t } = useAuth();
  return (
    <span className={`flex items-center gap-3 ${className}`}>
      <BrandMark />
      <span className="flex flex-col leading-tight">
        <span className="text-base font-bold tracking-tight">{t("app.name")}</span>
        {tagline && <span className="text-xs text-muted-foreground">{t("brand.tagline")}</span>}
      </span>
    </span>
  );
}
