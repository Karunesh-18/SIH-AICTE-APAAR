// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/auth", () => ({ useAuth: () => ({ t: (k: string) => k }) }));
import { RulePreviewPanel } from "../rule-preview-panel";

afterEach(cleanup);

describe("rule preview panel", () => {
  it("shows the counts, the institution table and the not-saved note", () => {
    render(<RulePreviewPanel preview={{
      code: "R10", cycle: 2026, current_params: {}, proposed_params: {}, current_count: 3,
      proposed_count: 5, added: 3, cleared: 1, added_examples: [], cleared_examples: [],
      by_institution: [{ institution_id: "i1", name: "Kaveri Valley College", current: 1, proposed: 2 }],
    }} />);
    expect(screen.getByTestId("current").textContent).toBe("3");
    expect(screen.getByTestId("proposed").textContent).toBe("5");
    expect(screen.getByTestId("added").textContent).toBe("+3");
    expect(screen.getByTestId("cleared").textContent).toBe("-1");
    expect(screen.getByText("Kaveri Valley College")).toBeTruthy();
    expect(screen.getByText("rules.preview.note")).toBeTruthy();
  });
});
