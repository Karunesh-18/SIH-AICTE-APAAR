export type UserForm = { email: string; full_name: string; role: string; institution_id: string; regions: string[]; password?: string };

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** Client-side hints only; the server validates again. Returns i18n keys by field. */
export function userFormErrors(f: UserForm, mode: "admin" | "staff"): Record<string, string> {
  const e: Record<string, string> = {};
  if (!EMAIL.test(f.email.trim())) e.email = "users.err.email";
  if (!f.full_name.trim()) e.full_name = "users.err.name";
  if (mode === "admin" && f.role.startsWith("INSTITUTION") && !f.institution_id) e.institution_id = "users.err.institution";
  if (f.password && f.password.length < 8) e.password = "users.err.password";
  return e;
}

export const staffPath = (inst: string, userId?: string, action?: string): string =>
  `/institutions/${inst}/staff${userId ? `/${userId}` : ""}${action ? `/${action}` : ""}`;
