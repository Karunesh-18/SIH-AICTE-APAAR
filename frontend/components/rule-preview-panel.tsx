"use client";
import { useAuth } from "@/lib/auth";
import type { RulePreview } from "@/lib/types";

export function RulePreviewPanel({ preview: p }: { preview: RulePreview }) {
  const { t } = useAuth();
  return (
    <section aria-label={t("rules.preview.title")} className="flex flex-col gap-3 rounded-md border border-border p-4 text-sm">
      <h3 className="font-medium">{t("rules.preview.title")} {p.cycle}</h3>
      <dl className="grid grid-cols-2 gap-2 tabular-nums sm:grid-cols-4">
        <div><dt className="text-muted-foreground">{t("rules.preview.current")}</dt><dd data-testid="current">{p.current_count}</dd></div>
        <div><dt className="text-muted-foreground">{t("rules.preview.proposed")}</dt><dd data-testid="proposed">{p.proposed_count}</dd></div>
        <div><dt className="text-muted-foreground">{t("rules.preview.added")}</dt><dd data-testid="added">+{p.added}</dd></div>
        <div><dt className="text-muted-foreground">{t("rules.preview.cleared")}</dt><dd data-testid="cleared">-{p.cleared}</dd></div>
      </dl>
      {p.by_institution.length > 0 && (
        <table className="w-full text-left tabular-nums">
          <thead>
            <tr>
              <th className="py-1 pr-2 font-medium">{t("rules.preview.institution")}</th>
              <th className="py-1 pr-2 font-medium">{t("rules.preview.current")}</th>
              <th className="py-1 font-medium">{t("rules.preview.proposed")}</th>
            </tr>
          </thead>
          <tbody>
            {p.by_institution.map((r) => (
              <tr key={r.institution_id}><td className="py-1 pr-2">{r.name}</td><td className="py-1 pr-2">{r.current}</td><td className="py-1">{r.proposed}</td></tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="text-muted-foreground">{t("rules.preview.note")}</p>
    </section>
  );
}
