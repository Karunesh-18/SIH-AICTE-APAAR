// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/verify/[token]/page";

vi.mock("next/navigation", () => ({ useParams: () => ({ token: "a.b.c" }) }));
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ t: (k: string) => k }) }));
vi.mock("@/components/consent-parts", () => ({ PublicFrame: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }));

afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear(); });

function show() {
  render(<QueryClientProvider client={new QueryClient()}><Page /></QueryClientProvider>);
}

describe("verify page offline fallback", () => {
  it("says there is no cached key when offline and nothing is cached", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    show();
    expect(await screen.findByText("verify.offline.noKey")).toBeTruthy();
  });
  it("reports the failure reason from the cached key check", async () => {
    localStorage.setItem("waymark.publicKey", JSON.stringify({ kty: "OKP", crv: "Ed25519", x: "AAAA" }));
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    show();
    expect(await screen.findByText("verify.offline.format")).toBeTruthy();
  });
});
