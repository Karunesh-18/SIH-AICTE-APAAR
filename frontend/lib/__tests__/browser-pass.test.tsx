// @vitest-environment jsdom
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { cleanup, render } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FilterSelect } from "@/components/filter-select";
import { ThemeToggle } from "@/components/theme-toggle";
import en from "../i18n/en.json";
import hi from "../i18n/hi.json";
import { formatDateTime, regionLabel } from "../status";

vi.mock("next-themes", () => ({ useTheme: () => ({ resolvedTheme: "dark", setTheme: () => {} }) }));
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ t: (k: string) => k }) }));

afterEach(cleanup);
const src = (p: string) => readFileSync(join(__dirname, "..", "..", p), "utf8");

describe("browser pass", () => {
  it("theme toggle renders the same on the server whatever the OS scheme", () => {
    expect(renderToString(<ThemeToggle />)).toContain("theme.toDark");
  });
  it("link-as-button sets nativeButton={false}", () => {
    expect(src("app/(app)/institution/page.tsx")).toMatch(/<Button nativeButton=\{false\} render=/);
  });
  it("dates follow the locale", () => {
    const iso = "2026-11-09T14:35:00Z";
    expect(formatDateTime(iso, "hi")).not.toBe(formatDateTime(iso, "en"));
    expect(formatDateTime(iso)).toBe(formatDateTime(iso, "en"));
  });
  it("regions translate, unknown names pass through", () => {
    const t = (k: string) => (hi as Record<string, string>)[k] ?? k;
    expect(regionLabel(t, "East")).not.toBe("East");
    expect(regionLabel(t, "Mars")).toBe("Mars");
    for (const r of ["East", "West", "North", "South"]) expect(en).toHaveProperty(`region.${r}`);
  });
  it("Hindi state labels carry no English word", () => {
    for (const s of ["Clear", "Alert", "Excess"]) expect(hi[`state.${s}` as keyof typeof hi]).not.toMatch(/[A-Za-z]/);
  });
  it("records status select shows the translated label", () => {
    expect(src("app/(app)/institution/records/page.tsx")).toMatch(/<SelectValue>\{/);
  });
  it("wide FilterSelect is not capped", () => {
    const { container } = render(<FilterSelect id="x" label="L" value="a" onChange={() => {}} options={[{ value: "a", label: "A" }]} wide />);
    expect(container.querySelector("select")!.className).not.toContain("max-w-56");
  });
  it("reports picker is wide", () => {
    expect(src("app/(app)/reports/page.tsx")).toMatch(/id="r-key"[^]*?noAny wide/);
  });
});
