"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { QRCodeSVG } from "qrcode.react";
import { QueryError } from "@/components/query-error";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDateTime } from "@/lib/status";

type Certificate = {
  token: string; qr_url: string; issued_at: string; expires_at: string;
  fields: { institution: string; name: string; apaar_id: string; student_id: string; programme: string; year_of_study: number };
};

/** Printable A4 certificate record. Opening it mints a signed CERTIFICATE token, which the server audits. */
export function CertificateRecord({ id }: { id: string }) {
  const { t } = useAuth();
  // Mints (and audits) once per visit: no refetch on focus.
  const q = useQuery<Certificate, ApiError>({
    queryKey: ["certificate", id],
    queryFn: () => api.post<Certificate>(`/records/${id}/certificate`),
    retry: false, refetchOnWindowFocus: false, staleTime: Infinity, gcTime: 0,
  });
  const f = q.data?.fields;
  const rows: [string, string | number][] = f ? [
    [t("cert.institution"), f.institution], [t("cert.name"), f.name], [t("cert.apaar"), f.apaar_id],
    [t("cert.studentId"), f.student_id], [t("cert.programme"), f.programme], [t("cert.year"), f.year_of_study],
  ] : [];

  return (
    <div className="certificate mx-auto flex max-w-[210mm] flex-col gap-6">
      <div className="flex items-center justify-between gap-3 print:hidden">
        <Link className="text-sm underline" href={`/institution/records/${id}`}>{t("cert.back")}</Link>
        <Button onClick={() => window.print()} disabled={!q.data}>{t("cert.print")}</Button>
      </div>
      {q.isPending && <Skeleton className="h-64 w-full" />}
      {q.isError && <QueryError error={q.error} onRetry={() => q.refetch()} />}
      {q.data && f && (
        <article className="flex flex-col gap-6 rounded-md border border-border p-8 print:border-black print:p-0">
          <h1 className="text-2xl font-semibold">{t("cert.title")}</h1>
          <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-3 tabular-nums">
            {rows.map(([k, v]) => (
              <div key={k} className="contents"><dt className="text-muted-foreground print:text-black">{k}</dt><dd className="font-medium">{v}</dd></div>
            ))}
          </dl>
          <div className="flex items-center gap-4">
            <QRCodeSVG value={q.data.qr_url} size={132} role="img" aria-label={t("cert.qrAlt")} />
            <p className="text-sm">
              {t("cert.scan")}
              <br />
              <span className="text-muted-foreground print:text-black">{t("cert.validUntil")} {formatDateTime(q.data.expires_at)}</span>
            </p>
          </div>
        </article>
      )}
      <footer className="border-t border-border pt-3 text-xs text-muted-foreground print:text-black">{t("app.notice")}</footer>
    </div>
  );
}
