"use client";
import { useAuth } from "@/lib/auth";

export function SkipLink() {
  const { t } = useAuth();
  return (
    <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded-md focus:bg-background focus:px-3 focus:py-2 focus:text-sm focus:ring-2 focus:ring-ring">
      {t("a11y.skip")}
    </a>
  );
}
