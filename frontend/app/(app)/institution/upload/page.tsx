"use client";
import { useRef, useState, type DragEvent } from "react";
import { useRouter } from "next/navigation";
import { Download, FileUp } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/page-header";
import { RoleGuard } from "@/components/role-guard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { FORMATS, formatFromName, validateUploadFile, type Format } from "@/lib/upload-file";
import type { UploadReceipt } from "@/lib/types";

async function download(fmt: "csv" | "xlsx") {
  const blob = await api.blob(`/templates/${fmt}`);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `students-template.${fmt}`;
  a.click();
  URL.revokeObjectURL(url);
}

function UploadForm() {
  const { t, user } = useAuth();
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [format, setFormat] = useState<Format>("csv");
  const [year, setYear] = useState(String(new Date().getFullYear()));
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [over, setOver] = useState(false);

  function pick(f: File | undefined) {
    if (!f) return;
    const err = validateUploadFile(f);
    setProblem(err);
    setFile(err ? null : f);
    const fmt = formatFromName(f.name);
    if (fmt) setFormat(fmt);
  }
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setOver(false);
    pick(e.dataTransfer.files[0]);
  };

  async function submit() {
    if (!file) return;
    setBusy(true);
    const form = new FormData();
    form.append("file", file);
    form.append("cycle_year", year);
    try {
      const r = await api.post<UploadReceipt>("/uploads", form);
      router.push(`/institution/uploads/${r.id}`);
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : t("error.generic"));
      setBusy(false);
    }
  }

  const yearOk = /^\d{4}$/.test(year);
  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <div
        onDragOver={(e) => { e.preventDefault(); setOver(true); }}
        onDragLeave={() => setOver(false)}
        onDrop={onDrop}
        className={`flex flex-col items-center gap-3 rounded-md border border-dashed p-8 text-center ${over ? "border-primary bg-accent" : "border-border"}`}
      >
        <FileUp aria-hidden className="size-6 text-muted-foreground" />
        <p className="text-sm">{file ? file.name : t("upload.drop")}</p>
        <Button type="button" variant="outline" size="sm" onClick={() => input.current?.click()}>
          {t("upload.choose")}
        </Button>
        <input ref={input} type="file" className="sr-only" tabIndex={-1} aria-label={t("upload.choose")}
               accept={FORMATS.map((f) => "." + f).join(",")} onChange={(e) => pick(e.target.files?.[0])} />
        {problem && <p role="alert" className="text-sm text-status-excess">{t(problem)}</p>}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <Label>{t("upload.format")}</Label>
          <Select value={format} onValueChange={(v) => setFormat(v as Format)}>
            <SelectTrigger aria-label={t("upload.format")}><SelectValue /></SelectTrigger>
            <SelectContent>
              {FORMATS.map((f) => <SelectItem key={f} value={f}>{f.toUpperCase()}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="year">{t("upload.year")}</Label>
          <Input id="year" inputMode="numeric" value={year} onChange={(e) => setYear(e.target.value)} />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button disabled={!file || !yearOk || busy || !user?.institution_id} onClick={submit}>
          {busy ? t("upload.sending") : t("upload.submit")}
        </Button>
        <span className="text-sm text-muted-foreground">{t("upload.template")}</span>
        {(["csv", "xlsx"] as const).map((f) => (
          <Button key={f} variant="outline" size="sm"
                  onClick={() => download(f).catch(() => toast.error(t("error.generic")))}>
            <Download data-icon="inline-start" /> {f.toUpperCase()}
          </Button>
        ))}
      </div>
      <p className="text-sm text-muted-foreground">{t("upload.advisory")}</p>
    </div>
  );
}

export default function Page() {
  const { t } = useAuth();
  return (
    <RoleGuard roles={["INSTITUTION_ADMIN", "INSTITUTION_STAFF"]}>
      <PageHeader title={t("upload.title")} description={t("upload.intro")} />
      <UploadForm />
    </RoleGuard>
  );
}
