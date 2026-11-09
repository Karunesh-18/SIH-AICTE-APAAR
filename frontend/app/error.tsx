"use client";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";

export default function GlobalError({ reset }: { error: Error; reset: () => void }) {
  const { t } = useAuth();
  return (
    <main id="main" role="alert" className="mx-auto flex min-h-screen max-w-md flex-col items-start justify-center gap-4 px-4">
      <AlertCircle aria-hidden className="size-8 text-status-excess" />
      <h1 className="text-2xl font-semibold">{t("error.title")}</h1>
      <p className="text-muted-foreground">{t("error.generic")}</p>
      <Button size="lg" className="min-h-11" onClick={reset}>{t("state.retry")}</Button>
    </main>
  );
}
