"use client";
import { Label } from "@/components/ui/label";

export const selectClass = "h-8 rounded-lg border border-input bg-transparent px-2 text-sm dark:bg-input/30";

export function FilterSelect({ id, label, value, onChange, options, any }: {
  id: string; label: string; value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[]; any: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={id}>{label}</Label>
      <select id={id} className={`${selectClass} max-w-56`} value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">{any}</option>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}
