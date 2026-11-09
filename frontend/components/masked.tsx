import { isMasked } from "@/lib/status";

/** Shows a value exactly as the API returned it; masking happens on the server, never here. */
export function Masked({ value, label }: { value: string | null | undefined; label: string }) {
  if (value == null || value === "") return <span>-</span>;
  if (!isMasked(value)) return <span>{value}</span>;
  return (
    <>
      <span title={label} className="font-mono text-muted-foreground">{value}</span>
      <span className="sr-only">{label}</span>
    </>
  );
}
