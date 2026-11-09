// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { StatusBadge, InstitutionStateBadge } from "../status-badge";

afterEach(cleanup);

describe("badges", () => {
  it("shows a label and an icon, not colour alone", () => {
    const { container } = render(<StatusBadge status="flagged" label="Flagged" />);
    expect(screen.getByText("Flagged")).toBeTruthy();
    expect(container.querySelector("svg")).not.toBeNull();
  });
  it("institution state has label and icon", () => {
    const { container } = render(<InstitutionStateBadge state="Excess" label="Excess" />);
    expect(screen.getByText("Excess")).toBeTruthy();
    expect(container.querySelector("svg")).not.toBeNull();
  });
});
