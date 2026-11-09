"use client";
import { useState, type ReactNode } from "react";
import { Check, Copy } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";

/** Checkbox list in a fieldset: one legend, optional hint, optional per-option description, one error. */
export function CheckGroup({ legend, hint, options, value, onChange, error, disabled }: {
  legend: string; hint?: string; options: { value: string; label: string; desc?: string }[];
  value: string[]; onChange: (v: string[]) => void; error?: string; disabled?: boolean;
}) {
  const toggle = (v: string) => onChange(value.includes(v) ? value.filter((x) => x !== v) : [...value, v]);
  return (
    <fieldset className="flex flex-col gap-2" disabled={disabled}>
      <legend className="text-sm font-medium">{legend}</legend>
      {hint && <p className="text-sm text-muted-foreground">{hint}</p>}
      <div className="flex flex-col gap-2">
        {options.map((o) => (
          <label key={o.value} className="flex items-start gap-2 text-sm">
            <input type="checkbox" className="mt-0.5 size-4 accent-primary" checked={value.includes(o.value)} onChange={() => toggle(o.value)} />
            <span>
              {o.label}
              {o.desc && <span className="block text-muted-foreground">{o.desc}</span>}
            </span>
          </label>
        ))}
      </div>
      {error && <p role="alert" className="text-sm text-status-excess">{error}</p>}
    </fieldset>
  );
}

export const FieldError = ({ msg }: { msg?: string }) => (msg ? <p role="alert" className="text-sm text-status-excess">{msg}</p> : null);

export function CopyButton({ text, label, doneLabel }: { text: string; label: string; doneLabel: string }) {
  const [done, setDone] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setDone(true);
      setTimeout(() => setDone(false), 2000);
    } catch {
      /* clipboard blocked: the text stays selectable on screen */
    }
  }
  return (
    <Button type="button" variant="outline" size="sm" onClick={copy}>
      {done ? <Check data-icon="inline-start" /> : <Copy data-icon="inline-start" />}
      <span aria-live="polite">{done ? doneLabel : label}</span>
    </Button>
  );
}

/** Frame for the public pages: no session, no app shell, and no mark that could pass for an official one. */
export function PublicFrame({ children }: { children: ReactNode }) {
  const { t } = useAuth();
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-xl flex-col gap-6 px-4 py-6">
      <header className="flex items-center justify-between">
        <p className="font-semibold">{t("app.name")}</p>
        <ThemeToggle />
      </header>
      <main className="flex flex-1 flex-col gap-6">{children}</main>
      <footer className="border-t border-border pt-4 text-xs text-muted-foreground">{t("verify.notice")}</footer>
    </div>
  );
}
