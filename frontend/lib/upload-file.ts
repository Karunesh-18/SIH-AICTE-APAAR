export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
export const FORMATS = ["csv", "xlsx", "xls", "json"] as const;
export type Format = (typeof FORMATS)[number];

export function formatFromName(name: string): Format | null {
  const ext = name.split(".").pop()?.toLowerCase();
  return (FORMATS as readonly string[]).includes(ext ?? "") ? (ext as Format) : null;
}

/** Returns an i18n key for the problem, or null when the file is acceptable. */
export function validateUploadFile(f: { name: string; size: number }): string | null {
  if (!formatFromName(f.name)) return "upload.err.type";
  if (f.size === 0) return "upload.err.empty";
  if (f.size > MAX_UPLOAD_BYTES) return "upload.err.size";
  return null;
}
