export type CorrectionForm = {
  apaar_id: string; name: string; dob: string; year_of_study: string;
  admission_date: string; admission_category: string;
};

/** Only filled fields are sent (PATCH semantics). null means nothing to save. */
export function buildCorrection(f: CorrectionForm): Record<string, string | number> | null {
  const out: Record<string, string | number> = {};
  for (const k of ["apaar_id", "name", "dob", "admission_date", "admission_category"] as const) {
    const v = f[k].trim();
    if (v) out[k] = v;
  }
  const y = Number(f.year_of_study);
  if (f.year_of_study.trim() && Number.isInteger(y) && y >= 1) out.year_of_study = y;
  return Object.keys(out).length ? out : null;
}
