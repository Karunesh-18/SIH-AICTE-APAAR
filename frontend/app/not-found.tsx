"use client";
import Link from "next/link";
import { FileQuestion } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";

export default function NotFound() {
  const { t } = useAuth();
  return (
    <main id="main" className="mx-auto flex min-h-screen max-w-md flex-col items-start justify-center gap-4 px-4">
      <FileQuestion aria-hidden className="size-8 text-muted-foreground" />
      <h1 className="text-2xl font-semibold">{t("notfound.title")}</h1>
      <p className="text-muted-foreground">{t("notfound.body")}</p>
      <Link href="/" className={buttonVariants({ variant: "default", size: "lg" }) + " min-h-11"}>{t("notfound.home")}</Link>
      <p className="text-xs text-muted-foreground">{t("app.notice")}</p>
    </main>
  );
}
