"use client";
import { useAuth } from "@/lib/auth";
import { errorKey } from "@/lib/guard";
import { ErrorState } from "./states";

export function QueryError({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { t } = useAuth();
  const key = errorKey(error);
  return <ErrorState message={t(key)} retryLabel={t("state.retry")} onRetry={key === "error.generic" ? onRetry : undefined} />;
}
