"use client";
import { Label } from "@/components/ui/label";

export const selectClass = "min-h-11 rounded-lg border border-input px-2 text-sm";

export function FilterSelect({ id, label, value, onChange, options, any, noAny }: {
  id: string; label: string; value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[]; any?: string; noAny?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={id}>{label}</Label>
      <select id={id} className={`${selectClass} max-w-56`} value={value} onChange={(e) => onChange(e.target.value)}>
        {!noAny && <option value="">{any}</option>}
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}
