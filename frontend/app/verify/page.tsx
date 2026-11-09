"use client";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { PublicFrame } from "@/components/consent-parts";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth";

/** Explains the QR page and lets someone paste a token (or the whole link) to check it. */
export default function Page() {
  const { t } = useAuth();
  const router = useRouter();
  const [v, setV] = useState("");
  function go(e: FormEvent) {
    e.preventDefault();
    const token = v.trim().split("/").filter(Boolean).pop();
    if (token) router.push(`/verify/${encodeURIComponent(token)}`);
  }
  return (
    <PublicFrame>
      <h1 className="text-xl font-semibold">{t("verify.indexTitle")}</h1>
      <p className="text-sm text-muted-foreground">{t("verify.indexBody")}</p>
      <form onSubmit={go} className="flex flex-col gap-3">
        <Label htmlFor="tok">{t("verify.indexLabel")}</Label>
        <Input id="tok" value={v} onChange={(e) => setV(e.target.value)} autoComplete="off" spellCheck={false} className="font-mono" />
        <Button type="submit" disabled={!v.trim()} className="min-h-11 self-start">{t("verify.indexGo")}</Button>
      </form>
    </PublicFrame>
  );
}
