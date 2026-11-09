import { describe, expect, it, vi } from "vitest";
import { ApiError, createApi, memoryStore } from "../api";

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

function setup(responses: Response[]) {
  const fetchFn = vi.fn(async () => responses.shift()!);
  const store = memoryStore({ access: "A1", refresh: "R1" });
  return { api: createApi({ baseUrl: "http://x/api/v1", fetchFn, store }), fetchFn, store };
}

describe("api client", () => {
  it("sends the bearer token and returns parsed json", async () => {
    const { api, fetchFn } = setup([json(200, { ok: 1 })]);
    expect(await api.get("/auth/me")).toEqual({ ok: 1 });
    const [url, init] = fetchFn.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("http://x/api/v1/auth/me");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer A1");
  });

  it("refreshes once on 401 then retries with the new token", async () => {
    const { api, fetchFn, store } = setup([
      json(401, { detail: "expired" }),
      json(200, { access_token: "A2" }),
      json(200, { ok: 2 }),
    ]);
    expect(await api.get("/auth/me")).toEqual({ ok: 2 });
    expect(fetchFn).toHaveBeenCalledTimes(3);
    expect(store.get().access).toBe("A2");
  });

  it("clears the session when refresh fails and throws ApiError 401", async () => {
    const { api, store } = setup([json(401, {}), json(401, {})]);
    await expect(api.get("/auth/me")).rejects.toMatchObject({ status: 401 });
    expect(store.get()).toEqual({ access: null, refresh: null });
  });

  it("does not loop: a second 401 after refresh is returned as an error", async () => {
    const { api, fetchFn } = setup([json(401, {}), json(200, { access_token: "A2" }), json(401, {})]);
    await expect(api.get("/x")).rejects.toBeInstanceOf(ApiError);
    expect(fetchFn).toHaveBeenCalledTimes(3);
  });

  it("surfaces the server detail message", async () => {
    const { api } = setup([json(403, { detail: "Out of scope" })]);
    await expect(api.get("/x")).rejects.toMatchObject({ status: 403, message: "Out of scope" });
  });

  it("login stores both tokens and does not send a bearer", async () => {
    const fetchFn = vi.fn(async () => json(200, { access_token: "N1", refresh_token: "N2" }));
    const store = memoryStore();
    const api = createApi({ baseUrl: "http://x/api/v1", fetchFn, store });
    await api.login("a@b.test", "pw");
    expect(store.get()).toEqual({ access: "N1", refresh: "N2" });
    const init = (fetchFn.mock.calls[0] as unknown as [string, RequestInit])[1];
    expect((init.headers as Record<string, string>).Authorization).toBeUndefined();
  });
});
