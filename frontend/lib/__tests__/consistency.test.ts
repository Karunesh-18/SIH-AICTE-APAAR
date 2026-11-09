import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import en from "../i18n/en.json";
import { navFor, type Role } from "../nav";

const root = join(__dirname, "..", "..");
const roles: Role[] = ["AICTE_ADMIN", "AICTE_OFFICER", "INSTITUTION_ADMIN", "INSTITUTION_STAFF", "VERIFIER"];

describe("nav", () => {
  it("every nav item resolves to a real page", () => {
    for (const r of roles)
      for (const n of navFor(r)) expect(existsSync(join(root, "app", "(app)", n.href, "page.tsx")), `${r} ${n.href}`).toBe(true);
  });
});

function walk(dir: string, out: string[] = []): string[] {
  for (const f of readdirSync(dir)) {
    if (f === "node_modules" || f === "__tests__" || f === ".next") continue;
    const p = join(dir, f);
    if (statSync(p).isDirectory()) walk(p, out);
    else if (/\.tsx?$/.test(f)) out.push(p);
  }
  return out;
}

describe("i18n keys", () => {
  it("every literal t(\"key\") in the source exists in English", () => {
    const missing: string[] = [];
    for (const f of [...walk(join(root, "app")), ...walk(join(root, "components"))]) {
      for (const m of readFileSync(f, "utf8").matchAll(/\bt\(\s*"([a-zA-Z][\w]*\.[\w.]+)"\s*\)/g))
        if (!(m[1] in en)) missing.push(`${f.slice(root.length)}: ${m[1]}`);
    }
    expect(missing).toEqual([]);
  });
});
