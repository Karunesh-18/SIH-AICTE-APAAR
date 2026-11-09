"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Masked } from "@/components/masked";
import { PageHeader } from "@/components/page-header";
import { RecordActions } from "@/components/record-actions";
import { QueryError } from "@/components/query-error";
import { RoleGuard } from "@/components/role-guard";
import { StatusBadge } from "@/components/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/auth";
import { evidenceLines } from "@/lib/flags";
import { formatDateTime } from "@/lib/status";
import type { RecordDetail } from "@/lib/types";
import { useApiQuery } from "@/lib/use-api";

function Detail() {
  const { id } = useParams<{ id: string }>();
  const { t } = useAuth();
  // This read is audited server-side (RECORD.VIEWED): fetch once, do not refetch on focus.
  const q = useApiQuery<RecordDetail>(`/records/${id}`, { refetchOnWindowFocus: false, staleTime: Infinity });
  const r = q.data;
  const m = t("record.masked");

  const fields: [string, React.ReactNode][] = r ? [
    [t("record.apaar"), <Masked key="a" value={r.apaar_id} label={m} />],
    [t("record.name"), <Masked key="n" value={r.name} label={m} />],
    [t("record.dob"), <Masked key="d" value={r.dob} label={m} />],
    [t("record.programme"), r.programme],
    [t("record.cycle"), r.cycle_year],
    [t("record.admission"), r.admission_date],
    [t("record.category"), r.admission_category ?? "-"],
    [t("record.row"), `${r.row_number} (${t("record.version")} ${r.version})`],
  ] : [];

  return (
    <>
      <PageHeader title={t("record.detail")} actions={<span className="flex gap-4 text-sm"><Link className="underline" href={`/institution/records/${id}/certificate`}>{t("cert.open")}</Link><Link className="underline" href="/institution/records">{t("record.back")}</Link></span>} />
      {q.isPending && <Skeleton className="h-40 w-full max-w-2xl" />}
      {q.isError && <QueryError error={q.error} onRetry={() => q.refetch()} />}
      {r && (
        <div className="flex max-w-3xl flex-col gap-8">
          <div>
            <StatusBadge status={r.status} label={t(`status.${r.status}`)} />
            <p className="mt-2 text-sm text-muted-foreground">{t("record.audited")}</p>
          </div>
          <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm tabular-nums">
            {fields.map(([k, v]) => (
              <div key={k} className="contents"><dt className="text-muted-foreground">{k}</dt><dd>{v}</dd></div>
            ))}
          </dl>
          <section aria-labelledby="fl-h" className="flex flex-col gap-3">
            <h2 id="fl-h" className="font-semibold">{t("record.flags")}</h2>
            {r.flags.length === 0 && <p className="text-sm">{t("record.noFlags")}</p>}
            <ul className="flex flex-col gap-3">
              {r.flags.map((f) => (
                <li key={f.id} className="rounded-md border border-border p-4 text-sm">
                  <p className="font-medium"><span className="font-mono">{f.rule_code}</span> - {t(`rule.${f.rule_code}`)}</p>
                  <p className="mt-1">{f.reason}</p>
                  <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
                    {evidenceLines(f.evidence).map((l) => (
                      <div key={l.key} className="contents">
                        <dt className="text-muted-foreground">{l.key.replace(/_/g, " ")}</dt><dd className="font-mono">{l.value}</dd>
                      </div>
                    ))}
                  </dl>
                </li>
              ))}
            </ul>
          </section>
          <section aria-labelledby="v-h" className="flex flex-col gap-3">
            <h2 id="v-h" className="font-semibold">{t("record.history")}</h2>
            <ol className="flex flex-col gap-2 text-sm">
              {r.versions.map((v) => (
                <li key={v.id} className="flex flex-wrap items-center gap-3 tabular-nums">
                  <span>{t("record.version")} {v.version}</span>
                  <StatusBadge status={v.status} label={t(`status.${v.status}`)} />
                  <span className="text-muted-foreground">
                    {v.is_current ? t("record.current") : `${t("record.superseded")} ${formatDateTime(v.superseded_at)}`}
                  </span>
                  <Link className="underline" href={`/institution/uploads/${v.upload_id}`}>{t("record.fromUpload")}</Link>
                </li>
              ))}
            </ol>
          </section>
          <RecordActions record={r} />
        </div>
      )}
    </>
  );
}

export default function Page() {
  return (
    <RoleGuard roles={["INSTITUTION_ADMIN", "INSTITUTION_STAFF"]}>
      <Detail />
    </RoleGuard>
  );
}
