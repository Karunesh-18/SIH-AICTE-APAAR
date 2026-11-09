// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { Masked } from "../masked";

afterEach(cleanup);

describe("Masked", () => {
  it("marks masked values and explains them to assistive tech", () => {
    render(<Masked value="R**** K***" label="Masked by the server" />);
    expect(screen.getByText("R**** K***").getAttribute("title")).toBe("Masked by the server");
    expect(screen.getByText("Masked by the server", { selector: ".sr-only" })).toBeTruthy();
  });
  it("shows plain values untouched and a dash for null", () => {
    render(<><Masked value="Ravi" label="m" /><Masked value={null} label="m" /></>);
    expect(screen.getByText("Ravi").getAttribute("title")).toBeNull();
    expect(screen.getByText("-")).toBeTruthy();
  });
});
