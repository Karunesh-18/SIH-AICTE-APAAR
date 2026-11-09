// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const post = vi.fn().mockResolvedValue({
  token: "tok.en.sig", qr_url: "http://localhost:3000/verify/tok.en.sig",
  issued_at: "2026-01-01T00:00:00Z", expires_at: "2031-01-01T00:00:00Z",
  fields: { institution: "Kaveri Valley College", name: "Aarav Nair", apaar_id: "111122223333",
    student_id: "rec-123", programme: "MBA", year_of_study: 2 },
});
vi.mock("@/lib/api", () => ({ api: { post: (...a: unknown[]) => post(...a) }, ApiError: class extends Error { status = 0; } }));
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ t: (k: string) => k }) }));
import { CertificateRecord } from "../certificate-record";

afterEach(() => { cleanup(); post.mockClear(); });
const open = () => render(
  <QueryClientProvider client={new QueryClient()}><CertificateRecord id="rec-123" /></QueryClientProvider>,
);

describe("certificate record", () => {
  it("mints once and renders every printed field", async () => {
    open();
    await screen.findByText("Aarav Nair");
    expect(post).toHaveBeenCalledTimes(1);
    expect(post).toHaveBeenCalledWith("/records/rec-123/certificate");
    for (const v of ["Kaveri Valley College", "111122223333", "rec-123", "MBA", "2"]) {
      expect(document.body.textContent).toContain(v);
    }
  });
  it("shows a QR code and the prototype footer", async () => {
    open();
    await screen.findByText("Aarav Nair");
    expect(screen.getByRole("img", { name: "cert.qrAlt" })).toBeTruthy();
    expect(screen.getByText("app.notice")).toBeTruthy();
  });
  it("Print button calls window.print", async () => {
    const print = vi.fn();
    vi.stubGlobal("print", print);
    open();
    await screen.findByText("Aarav Nair");
    fireEvent.click(await screen.findByRole("button", { name: "cert.print" }));
    expect(print).toHaveBeenCalledTimes(1);
    vi.unstubAllGlobals();
  });
});
