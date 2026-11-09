// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const post = vi.fn();
let demo = true;
const cp = { seq: 7, hash: "abcdef0123456789", count: 42, signed_at: "2026-01-01T00:00:00Z", token: "tok.en" };
vi.mock("@/lib/api", () => ({ api: { post: (...a: unknown[]) => post(...a) }, ApiError: class extends Error { status = 0; } }));
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ t: (k: string) => (k === "audit.cp.created" ? "#{seq} {hash} {n} {when}" : k) }) }));
vi.mock("@/components/role-guard", () => ({ RoleGuard: ({ children }: { children: React.ReactNode }) => <>{children}</> }));
vi.mock("@tanstack/react-query", () => ({ useQueryClient: () => ({ invalidateQueries: vi.fn() }) }));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock("@/lib/use-api", () => ({
  useApiQuery: (path: string) => {
    const base = { isPending: false, isError: false, refetch: vi.fn() };
    if (path === "/admin/clock") return { ...base, data: { demo_mode: demo } };
    if (path === "/audit/checkpoints") return { ...base, data: [cp] };
    return { ...base, data: { items: [], total: 0 } };
  },
}));
import Page from "@/app/(app)/admin/audit/page";

afterEach(() => { cleanup(); post.mockReset(); demo = true; });

async function verifyWith(checkpoint: unknown) {
  post.mockResolvedValue({ ok: true, count: 3, first_broken_id: null, checkpoint });
  render(<Page />);
  fireEvent.click(screen.getByRole("button", { name: "audit.verify" }));
}

describe("audit checkpoints", () => {
  it.each([
    [{ ok: true, reason: null }, "audit.cp.ok"],
    [{ ok: false, reason: "missing_rows" }, "audit.cp.missing"],
    [{ ok: false, reason: "hash_mismatch" }, "audit.cp.hash"],
    [{ ok: false, reason: "bad_signature" }, "audit.cp.sig"],
    [null, "audit.cp.none"],
  ])("renders outcome %j", async (c, key) => {
    await verifyWith(c);
    expect(await screen.findByText(key)).toBeTruthy();
  });
  it("hides demo buttons outside demo mode", () => {
    demo = false;
    render(<Page />);
    expect(screen.queryByRole("button", { name: /audit.truncate/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /audit.tamper/ })).toBeNull();
  });
  it("shows the demo truncate button in demo mode", () => {
    render(<Page />);
    expect(screen.getByRole("button", { name: /audit.truncate/ })).toBeTruthy();
  });
  it("create shows the returned seq", async () => {
    post.mockResolvedValue(cp);
    render(<Page />);
    fireEvent.click(screen.getByRole("button", { name: "audit.cp.create" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/admin/audit/checkpoint"));
    expect((await screen.findByTestId("cp-new")).textContent).toContain("#7 abcdef012345 42");
  });
});
