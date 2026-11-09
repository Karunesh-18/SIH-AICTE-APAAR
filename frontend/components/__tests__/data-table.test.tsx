// @vitest-environment jsdom
import { cleanup, render, screen, fireEvent } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { DataTable } from "../data-table";

afterEach(cleanup);
const cols = [{ accessorKey: "name", header: "Name" }];
const labels = { empty: "Nothing here", error: "Broke", retry: "Retry", prev: "Prev", next: "Next" };

describe("DataTable", () => {
  it("renders rows", () => {
    render(<DataTable columns={cols} data={[{ name: "A" }, { name: "B" }]} labels={labels} />);
    expect(screen.getByText("A")).toBeTruthy();
  });
  it("shows empty state", () => {
    render(<DataTable columns={cols} data={[]} labels={labels} />);
    expect(screen.getByText("Nothing here")).toBeTruthy();
  });
  it("shows error state with retry", () => {
    let n = 0;
    render(<DataTable columns={cols} data={[]} error="oops" onRetry={() => n++} labels={labels} />);
    fireEvent.click(screen.getByText("Retry"));
    expect(n).toBe(1);
  });
  it("shows loading skeletons", () => {
    const { container } = render(<DataTable columns={cols} data={[]} loading labels={labels} />);
    expect(container.querySelectorAll("[data-slot=skeleton]").length).toBeGreaterThan(0);
  });
  it("pages server-side", () => {
    let off = -1;
    render(<DataTable columns={cols} data={[{ name: "A" }]} labels={labels}
      paging={{ total: 60, limit: 25, offset: 0, onOffset: (o) => (off = o) }} />);
    fireEvent.click(screen.getByText("Next"));
    expect(off).toBe(25);
  });
});
