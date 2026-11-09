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

  it("stores the rotated refresh token returned by refresh", async () => {
    const { api, store } = setup([
      json(401, {}),
      json(200, { access_token: "A2", refresh_token: "R2" }),
      json(200, {}),
    ]);
    await api.get("/x");
    expect(store.get()).toEqual({ access: "A2", refresh: "R2" });
  });

  it("sends only one refresh call for concurrent 401s", async () => {
    const calls: string[] = [];
    const fetchFn = vi.fn(async (url: string, init?: RequestInit) => {
      const path = url.replace("http://x/api/v1", "");
      calls.push(path);
      if (path === "/auth/refresh") {
        await new Promise((r) => setTimeout(r, 5));
        return json(200, { access_token: "A2", refresh_token: "R2" });
      }
      const auth = (init?.headers as Record<string, string>).Authorization;
      return auth === "Bearer A2" ? json(200, { ok: 1 }) : json(401, {});
    });
    const store = memoryStore({ access: "A1", refresh: "R1" });
    const api = createApi({ baseUrl: "http://x/api/v1", fetchFn: fetchFn as unknown as typeof fetch, store });
    await Promise.all([api.get("/a"), api.get("/b"), api.get("/c")]);
    expect(calls.filter((c) => c === "/auth/refresh")).toHaveLength(1);
    expect(store.get().refresh).toBe("R2");
  });

  it("signs out cleanly when refresh is refused", async () => {
    const { api, store } = setup([json(401, {}), json(401, { detail: "Invalid or expired token" })]);
    await expect(api.get("/x")).rejects.toMatchObject({ status: 401 });
    expect(store.get()).toEqual({ access: null, refresh: null });
    expect(api.hasSession()).toBe(false);
  });

  it("logout tells the server and clears the session", async () => {
    const { api, fetchFn, store } = setup([new Response(null, { status: 204 })]);
    api.logout();
    expect(store.get()).toEqual({ access: null, refresh: null });
    const [url, init] = fetchFn.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("http://x/api/v1/auth/logout");
    expect(init.body).toBe(JSON.stringify({ refresh_token: "R1" }));
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

  it("downloads a blob with the auth header, and supports put and delete", async () => {
    const { api, fetchFn } = setup([
      new Response("a,b", { status: 200 }), json(200, { v: 1 }), json(200, { v: 2 }),
    ]);
    const b = await api.blob("/templates/csv");
    expect(await b.text()).toBe("a,b");
    await api.put("/x", { a: 1 });
    await api.del("/y");
    const calls = fetchFn.mock.calls as unknown as [string, RequestInit][];
    expect((calls[0][1].headers as Record<string, string>).Authorization).toBe("Bearer A1");
    expect(calls[1][1].method).toBe("PUT");
    expect(calls[2][1].method).toBe("DELETE");
  });
});
