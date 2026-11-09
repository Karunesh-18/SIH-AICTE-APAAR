export type Role =
  | "AICTE_ADMIN"
  | "AICTE_OFFICER"
  | "INSTITUTION_ADMIN"
  | "INSTITUTION_STAFF"
  | "VERIFIER";

export type NavItem = { href: string; key: string };

const AICTE: NavItem[] = [
  { href: "/aicte", key: "nav.dashboard" },
  { href: "/review", key: "nav.review" },
  { href: "/reports", key: "nav.reports" },
  { href: "/verifications", key: "nav.verifications" },
];
const INSTITUTION: NavItem[] = [
  { href: "/institution", key: "nav.home" },
  { href: "/institution/upload", key: "nav.upload" },
  { href: "/institution/records", key: "nav.records" },
  { href: "/institution/flags", key: "nav.flags" },
  { href: "/institution/consents", key: "nav.consents" },
  { href: "/institution/verifications", key: "nav.verifications" },
];
const ADMIN_ONLY: NavItem[] = [
  { href: "/admin/rules", key: "nav.rules" },
  { href: "/admin/policies", key: "nav.policies" },
  { href: "/admin/verifiers", key: "nav.verifiers" },
  { href: "/admin/users", key: "nav.users" },
  { href: "/admin/windows", key: "nav.windows" },
  { href: "/admin/audit", key: "nav.audit" },
  { href: "/admin/clock", key: "nav.clock" },
];
const ADMIN_EXTRA: NavItem[] = [
  { href: "/institution/api-keys", key: "nav.apiKeys" },
  { href: "/institution/staff", key: "nav.staff" },
];

export function navFor(role: Role): NavItem[] {
  switch (role) {
    case "AICTE_ADMIN":
      return [...AICTE, ...ADMIN_ONLY];
    case "AICTE_OFFICER":
      return AICTE;
    case "INSTITUTION_ADMIN":
      return [...INSTITUTION, ...ADMIN_EXTRA];
    case "INSTITUTION_STAFF":
      return INSTITUTION;
    case "VERIFIER":
      return [{ href: "/verifier", key: "nav.verifier" }];
  }
}

export const homeFor = (role: Role): string => navFor(role)[0].href;
