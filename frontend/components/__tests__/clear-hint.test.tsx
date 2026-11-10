// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import en from "../../lib/i18n/en.json";
import hi from "../../lib/i18n/hi.json";

const dict = en as Record<string, string>;
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ t: (k: string) => dict[k] ?? k }) }));
import { ClearHint } from "../clear-hint";

afterEach(cleanup);

describe("ClearHint", () => {
  it("fills the template from values under a To clear: prefix", () => {
    render(<ClearHint hint={{ key: "hint.R06", values: { allowed: 60, excess: 1 } }} />);
    const text = screen.getByText(/^To clear:/).textContent ?? "";
    expect(text).toContain("60");
    expect(text).toContain("1 fewer");
    expect(text).not.toMatch(/[{}]/);
  });
  it("renders nothing when the hint is null or absent", () => {
    const { container, rerender } = render(<ClearHint hint={null} />);
    expect(container.textContent).toBe("");
    rerender(<ClearHint hint={undefined} />);
    expect(container.textContent).toBe("");
  });
  it("has en and hi text for all 12 rules, never forbidden words", () => {
    for (let i = 1; i <= 12; i++) {
      const k = `hint.R${String(i).padStart(2, "0")}`;
      for (const d of [en, hi] as Record<string, string>[]) expect(d[k]?.trim()).toBeTruthy();
      expect((en as Record<string, string>)[k]).not.toMatch(/penalt|reject|must/i);
      expect((hi as Record<string, string>)[k]).toMatch(/[ऀ-ॿ]/);
    }
  });
});
