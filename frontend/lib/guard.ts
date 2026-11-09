import { ApiError } from "./api";
import type { Role } from "./nav";

export const allowed = (role: Role | undefined, roles: Role[]): boolean => !!role && roles.includes(role);

export function errorKey(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 403) return "error.forbidden";
    if (e.status === 404) return "error.notFound";
  }
  return "error.generic";
}
