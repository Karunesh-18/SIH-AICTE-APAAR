// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const del = vi.fn().mockResolvedValue(undefined);
vi.mock("@/lib/api", () => ({ api: { del: (...a: unknown[]) => del(...a), post: vi.fn() }, ApiError: class extends Error { status = 0; } }));
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ t: (k: string) => k }) }));
vi.mock("@tanstack/react-query", () => ({ useQueryClient: () => ({ invalidateQueries: vi.fn() }) }));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock("@/lib/use-api", () => ({
  useApiQuery: () => ({
    isPending: false, isError: false, refetch: vi.fn(),
    data: { items: [{ id: "c1", apaar_id: "111122223333", purposes: ["scholarship", "admission"], fields: ["name"], source: "form",
      given_at: "2026-01-01T00:00:00Z", expires_at: "2099-01-01T00:00:00Z", withdrawn_at: null }] },
  }),
}));
import { ConsentsManager } from "../consents-manager";

afterEach(() => { cleanup(); del.mockClear(); });
const open = () => { render(<ConsentsManager />); fireEvent.click(screen.getByRole("button", { name: "consent.withdraw" })); };

describe("withdraw confirmation", () => {
  it("opens a dialog naming the student and purposes, sends nothing", async () => {
    open();
    const d = await screen.findByRole("dialog");
    expect(d.textContent).toContain("111122223333");
    expect(d.textContent).toContain("purpose.scholarship");
    expect(d.textContent).toContain("purpose.admission");
    expect(del).not.toHaveBeenCalled();
  });
  it("cancel sends nothing and closes", async () => {
    open();
    fireEvent.click(await screen.findByRole("button", { name: "dialog.cancel" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(del).not.toHaveBeenCalled();
  });
  it("confirm sends exactly one request", async () => {
    open();
    fireEvent.click(await screen.findByRole("button", { name: "consent.withdrawConfirm" }));
    await waitFor(() => expect(del).toHaveBeenCalledTimes(1));
    expect(del).toHaveBeenCalledWith("/consents/c1");
  });
});
