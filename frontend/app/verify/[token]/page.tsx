"use client";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { Suspense } from "react";
import { AlertTriangle, Ban, Check, Clock, ShieldQuestion } from "lucide-react";
import { PublicFrame } from "@/components/consent-parts";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fieldLabelKey, formatFieldValue, groupKid, verifyView } from "@/lib/consent";
import { formatDateTime } from "@/lib/status";
import type { PublicCheck, PublicKey } from "@/lib/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const ICONS = { check: Check, clock: Clock, ban: Ban, alert: AlertTriangle };
const TONES = {
  clear: "border-status-clear/40 bg-status-clear-bg text-status-clear",
  alert: "border-status-alert/40 bg-status-alert-bg text-status-alert",
  excess: "border-status-excess/40 bg-status-excess-bg text-status-excess",
};

function KeyInfo() {
  const { t } = useAuth();
  const k = useQuery<PublicKey, ApiError>({ queryKey: ["public-key"], queryFn: () => api.get<PublicKey>("/verify/public-key"), retry: false });
  return (
    <section className="flex flex-col gap-1 text-sm" aria-labelledby="key-h">
      <h2 id="key-h" className="font-medium">{t("verify.keyTitle")}</h2>
      {k.isPending && <p className="text-muted-foreground">{t("verify.keyLoading")}</p>}
      {k.isError && <p className="text-muted-foreground">{t("verify.keyUnavailable")}</p>}
      {k.data && (
        <p>
          <span className="text-muted-foreground">{t("verify.keyId")}: </span>
          <code className="font-mono">{groupKid(k.data.jwk.kid)}</code>
        </p>
      )}
      <a className="w-fit underline underline-offset-4" href={`${BASE}/verify/public-key`} target="_blank" rel="noreferrer">{t("verify.keyLink")}</a>
    </section>
  );
}

function CheckResult() {
  const { token } = useParams<{ token: string }>();
  const { t } = useAuth();
  // Public: a raw fetch, so no Authorization header is ever attached.
  const q = useQuery<PublicCheck, ApiError>({
    queryKey: ["public-check", token],
    queryFn: async () => {
      const res = await fetch(`${BASE}/verify/${encodeURIComponent(token)}`);
      if (!res.ok) throw new ApiError(res.status, res.statusText);
      return res.json();
    },
    retry: false,
    refetchOnWindowFocus: false,
  });
  const v = q.data ? verifyView(q.data.status) : null;
  const Icon = v ? ICONS[v.icon] : ShieldQuestion;

  return (
    <PublicFrame>
      <h1 className="text-xl font-semibold">{t("verify.title")}</h1>
      {q.isPending && (
        <div role="status" aria-live="polite" className="flex flex-col gap-3">
          <p className="text-muted-foreground">{t("verify.checking")}</p>
          <Skeleton className="h-28 w-full" />
        </div>
      )}
      {q.isError && (
        <div role="alert" className="flex flex-col items-start gap-3 rounded-md border border-border p-4">
          <p className="text-sm">{q.error.status === 429 ? t("verify.limited") : t("verify.unreachable")}</p>
          <Button variant="outline" size="sm" onClick={() => q.refetch()}>{t("state.retry")}</Button>
        </div>
      )}
      {q.data && v && (
        <>
          <section role="status" aria-live="polite" className={`flex flex-col gap-2 rounded-md border p-4 ${TONES[v.tone]}`}>
            <p className="flex items-center gap-2 text-lg font-semibold">
              <Icon aria-hidden className="size-6" />
              {t(v.titleKey)}
            </p>
            <p className="text-sm text-foreground">
              {t(v.status === "GENUINE" && q.data.purpose === "CERTIFICATE" ? "verify.genuine.cert.body" : v.bodyKey)}
            </p>
          </section>
          {v.showFields && q.data.fields && (
            <section aria-labelledby="conf-h" className="flex flex-col gap-2">
              <h2 id="conf-h" className="font-medium">{t("verify.confirmed")}</h2>
              <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 rounded-md border border-border p-4 text-sm">
                {Object.entries(q.data.fields).map(([f, val]) => (
                  <div key={f} className="contents">
                    <dt className="text-muted-foreground">{t(fieldLabelKey(f))}</dt>
                    <dd className="font-medium">{formatFieldValue(f, val)}</dd>
                  </div>
                ))}
              </dl>
            </section>
          )}
          {v.showMeta && (
            <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-sm">
              <dt className="text-muted-foreground">{t("verify.purpose")}</dt>
              <dd>{q.data.purpose ? t(`purpose.${q.data.purpose}`) : "-"}</dd>
              <dt className="text-muted-foreground">{t("verify.issuer")}</dt>
              <dd>{q.data.issuer ?? "-"}</dd>
              <dt className="text-muted-foreground">{t("verify.issuedAt")}</dt>
              <dd>{formatDateTime(q.data.issued_at)}</dd>
              <dt className="text-muted-foreground">{t("verify.expiresAt")}</dt>
              <dd>{formatDateTime(q.data.expires_at)}</dd>
            </dl>
          )}
        </>
      )}
      <KeyInfo />
      <section aria-labelledby="how-h" className="flex flex-col gap-2 text-sm">
        <h2 id="how-h" className="font-medium">{t("verify.howTitle")}</h2>
        <ol className="list-decimal space-y-1 pl-5 text-muted-foreground">
          <li>{t("verify.how1")}</li>
          <li>{t("verify.how2")}</li>
          <li>{t("verify.how3")}</li>
        </ol>
      </section>
    </PublicFrame>
  );
}

// useParams suspends under Cache Components, so the page needs a boundary.
export default function Page() {
  return (
    <Suspense fallback={<main className="p-8 text-muted-foreground">Checking...</main>}>
      <CheckResult />
    </Suspense>
  );
}
