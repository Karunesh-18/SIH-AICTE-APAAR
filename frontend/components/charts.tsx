"use client";
import { useState, type ReactNode } from "react";
import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAuth } from "@/lib/auth";
import { intakeBars, ruleColor, ruleStack, type InstRow } from "@/lib/dash";

const AXIS = { fontSize: 12, fill: "var(--muted-foreground)" };
const shorten = (s: string, n = 24) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);

function Figure({ title, note, chart, table }: { title: string; note?: string; chart: ReactNode; table: ReactNode }) {
  const { t } = useAuth();
  const [asTable, setAsTable] = useState(false);
  return (
    <figure className="flex flex-col gap-3 rounded-md border border-border bg-card p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <figcaption>
          <h2 className="font-semibold">{title}</h2>
          {note && <p className="mt-0.5 max-w-prose text-sm text-muted-foreground">{note}</p>}
        </figcaption>
        <Button variant="outline" size="sm" aria-pressed={asTable} onClick={() => setAsTable((v) => !v)}>
          {t(asTable ? "chart.viewChart" : "chart.viewTable")}
        </Button>
      </div>
      {asTable ? <div className="overflow-x-auto">{table}</div> : chart}
    </figure>
  );
}

/** Pattern swatch so "Excess" is never carried by colour alone. */
function Hatch() {
  return (
    <defs>
      <pattern id="hatch-excess" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width="6" height="6" fill="var(--status-excess-bg)" />
        <line x1="0" y1="0" x2="0" y2="6" stroke="var(--status-excess)" strokeWidth="3" />
      </pattern>
    </defs>
  );
}

export function IntakeChart({ rows }: { rows: InstRow[] }) {
  const { t } = useAuth();
  const bars = intakeBars(rows);
  const h = bars.length * 30 + 40;
  const chart = (
    <>
      <div role="img" aria-label={t("chart.intake.alt")} style={{ height: h }} className="w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={bars} layout="vertical" margin={{ top: 4, right: 150, bottom: 4, left: 0 }} barCategoryGap={6}>
            <Hatch />
            <CartesianGrid horizontal={false} stroke="var(--border)" />
            <XAxis type="number" tick={AXIS} axisLine={false} tickLine={false} allowDecimals={false} />
            <YAxis type="category" dataKey="name" width={150} tick={AXIS} tickLine={false} axisLine={false}
                   tickFormatter={(v: string) => shorten(v)} />
            <Tooltip cursor={{ fill: "var(--muted)" }} content={({ payload }) => {
              const r = payload?.[0]?.payload as (typeof bars)[number] | undefined;
              return r ? (
                <div className="rounded-md border border-border bg-popover p-2 text-xs tabular-nums shadow-none">
                  <p className="font-medium">{r.name}</p>
                  <p>{t("chart.enrolled")}: {r.enrolled}</p>
                  <p>{t("chart.allowed")}: {r.allowed}</p>
                </div>
              ) : null;
            }} />
            <Bar dataKey="within" stackId="s" fill="var(--chart-1)" stroke="var(--card)" strokeWidth={2} />
            <Bar dataKey="headroom" stackId="s" fill="var(--chart-track)" stroke="var(--card)" strokeWidth={2} />
            <Bar dataKey="over" stackId="s" fill="url(#hatch-excess)" stroke="var(--status-excess)" strokeWidth={1.5}
                 radius={[0, 4, 4, 0]}>
              <LabelList dataKey="over" content={(p) => {
                const { x = 0, y = 0, width = 0, height = 0, index = 0 } = p as Record<string, number>;
                const r = bars[index];
                return (
                  <text x={x + width + 8} y={y + height / 2} dominantBaseline="central" fontSize={12} fill="var(--foreground)"
                        className="tabular">
                    {r.enrolled}/{r.allowed}{r.excess ? `  ${t("state.Excess")} +${r.over}` : ""}
                  </text>
                );
              }} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <ul className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted-foreground" aria-label={t("chart.legend")}>
        <li className="flex items-center gap-1.5"><i className="inline-block size-3 rounded-sm" style={{ background: "var(--chart-1)" }} />{t("chart.enrolledWithin")}</li>
        <li className="flex items-center gap-1.5"><i className="inline-block size-3 rounded-sm" style={{ background: "var(--chart-track)" }} />{t("chart.headroom")}</li>
        <li className="flex items-center gap-1.5"><i className="inline-block size-3 rounded-sm border" style={{ borderColor: "var(--status-excess)", background: "repeating-linear-gradient(45deg, var(--status-excess) 0 2px, var(--status-excess-bg) 2px 5px)" }} />{t("chart.overCap")}</li>
        <li>{t("chart.capNote")}</li>
      </ul>
    </>
  );
  const table = (
    <Table className="tabular-nums">
      <TableHeader><TableRow>
        <TableHead>{t("col.institution")}</TableHead><TableHead>{t("chart.enrolled")}</TableHead>
        <TableHead>{t("chart.allowed")}</TableHead><TableHead>{t("chart.over")}</TableHead>
      </TableRow></TableHeader>
      <TableBody>{bars.map((r) => (
        <TableRow key={r.id}><TableCell>{r.name}</TableCell><TableCell>{r.enrolled}</TableCell>
          <TableCell>{r.allowed}</TableCell><TableCell>{r.over || "-"}</TableCell></TableRow>
      ))}</TableBody>
    </Table>
  );
  return <Figure title={t("chart.intake.title")} note={t("chart.intake.note")} chart={chart} table={table} />;
}

export function RulesChart({ rows }: { rows: { month: string; rule: string; count: number }[] }) {
  const { t } = useAuth();
  const { data, keys } = ruleStack(rows);
  const full = data.map((d) => {
    const o: Record<string, number | string> = { ...d };
    for (const k of keys) o[k] = (d[k] as number) ?? 0;
    o.total = keys.reduce((n, k) => n + (o[k] as number), 0);
    return o;
  });
  const name = (k: string) => (k === "other" ? t("chart.otherRules") : `${k} ${t(`rule.${k}`)}`);
  const sum = (k: string) => full.reduce((n, d) => n + (d[k] as number), 0);
  const chart = (
    <>
      <div role="img" aria-label={t("chart.rules.alt")} className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={full} margin={{ top: 20, right: 8, bottom: 4, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--border)" />
            <XAxis dataKey="month" tick={AXIS} tickLine={false} axisLine={false} />
            <YAxis tick={AXIS} tickLine={false} axisLine={false} allowDecimals={false} width={32} />
            <Tooltip cursor={{ fill: "var(--muted)" }} content={({ payload, label }) => (
              <div className="rounded-md border border-border bg-popover p-2 text-xs tabular-nums">
                <p className="font-medium">{label}</p>
                {payload?.filter((p) => Number(p.value) > 0).map((p) => (
                  <p key={String(p.dataKey)}>{name(String(p.dataKey))}: {p.value}</p>
                ))}
              </div>
            )} />
            {keys.map((k, i) => (
              <Bar key={k} dataKey={k} stackId="s" fill={ruleColor(k)} stroke="var(--card)" strokeWidth={2}
                   radius={i === keys.length - 1 ? [4, 4, 0, 0] : 0}>
                {i === keys.length - 1 && (
                  <LabelList dataKey="total" position="top" fill="var(--foreground)" fontSize={12} />
                )}
              </Bar>
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <ul className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted-foreground" aria-label={t("chart.legend")}>
        {keys.map((k) => (
          <li key={k} className="flex items-center gap-1.5">
            <i className="inline-block size-3 rounded-sm" style={{ background: ruleColor(k) }} />
            <span className="text-foreground">{name(k)}</span> <span className="tabular">({sum(k)})</span>
          </li>
        ))}
      </ul>
    </>
  );
  const table = (
    <Table className="tabular-nums">
      <TableHeader><TableRow>
        <TableHead>{t("chart.month")}</TableHead>
        {keys.map((k) => <TableHead key={k}>{name(k)}</TableHead>)}
        <TableHead>{t("chart.total")}</TableHead>
      </TableRow></TableHeader>
      <TableBody>{full.map((d) => (
        <TableRow key={String(d.month)}><TableCell>{d.month}</TableCell>
          {keys.map((k) => <TableCell key={k}>{d[k] || "-"}</TableCell>)}
          <TableCell>{d.total}</TableCell></TableRow>
      ))}</TableBody>
    </Table>
  );
  return <Figure title={t("chart.rules.title")} note={t("chart.rules.note")} chart={chart} table={table} />;
}
