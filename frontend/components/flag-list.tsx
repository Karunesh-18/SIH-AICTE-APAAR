"use client";
import { useAuth } from "@/lib/auth";
import { explainFlag } from "@/lib/flags";
import type { FlagItem } from "@/lib/types";

/** One flag: rule code, the sentence the server wrote, the evidence numbers and the rows. */
export function FlagCard({ flag }: { flag: FlagItem }) {
  const { t } = useAuth();
  const e = explainFlag(flag);
  return (
    <li className="rounded-md border border-border p-4">
      <p className="flex items-center gap-2 text-sm font-medium">
        <span className="rounded bg-status-alert-bg px-1.5 py-0.5 font-mono text-xs text-status-alert">{e.code}</span>
        {t(`rule.${e.code}`)}
      </p>
      <p className="mt-2 text-sm">{e.reason}</p>
      {e.lines.length > 0 && (
        <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm tabular-nums">
          {e.lines.map((l) => (
            <div key={l.key} className="contents">
              <dt className="text-muted-foreground">{l.key.replace(/_/g, " ")}</dt>
              <dd className="font-mono">{l.value}</dd>
            </div>
          ))}
          {e.rows && (
            <div className="contents">
              <dt className="text-muted-foreground">{t("flag.rows")}</dt>
              <dd className="font-mono">{e.rows}</dd>
            </div>
          )}
        </dl>
      )}
      {e.note && <p className="mt-3 text-sm text-muted-foreground">{t(e.note)}</p>}
    </li>
  );
}
