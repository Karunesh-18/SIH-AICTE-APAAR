export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

type Session = { access: string | null; refresh: string | null };
export type TokenStore = { get(): Session; set(s: Session): void };

export function memoryStore(initial?: Partial<Session>): TokenStore {
  let s: Session = { access: null, refresh: null, ...initial };
  return { get: () => s, set: (n) => (s = n) };
}

// ponytail: tokens in localStorage are readable by any XSS; move to httpOnly cookies behind a proxy for production.
export function browserStore(): TokenStore {
  const KEY = "waymark.session";
  return {
    get() {
      try {
        return JSON.parse(localStorage.getItem(KEY) ?? "") as Session;
      } catch {
        return { access: null, refresh: null };
      }
    },
    set(s) {
      try {
        if (s.access || s.refresh) localStorage.setItem(KEY, JSON.stringify(s));
        else localStorage.removeItem(KEY);
      } catch {
        /* storage blocked: session lasts until reload */
      }
    },
  };
}

type Opts = { baseUrl: string; fetchFn?: typeof fetch; store: TokenStore };

export function createApi({ baseUrl, fetchFn = (...a) => fetch(...a), store }: Opts) {
  async function raw(path: string, method: string, body?: unknown, auth = true, keepalive = false) {
    const headers: Record<string, string> = {};
    if (body !== undefined && !(body instanceof FormData)) headers["Content-Type"] = "application/json";
    const token = store.get().access;
    if (auth && token) headers.Authorization = `Bearer ${token}`;
    return fetchFn(baseUrl + path, {
      method,
      keepalive,
      headers,
      body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
    });
  }

  // One refresh in flight per tab: the refresh token is single-use, so a second call would be a replay.
  let inflight: Promise<boolean> | null = null;
  function refresh(): Promise<boolean> {
    inflight ??= doRefresh().finally(() => (inflight = null));
    return inflight;
  }

  async function doRefresh(): Promise<boolean> {
    const { refresh: rt } = store.get();
    if (!rt) return false;
    const res = await raw("/auth/refresh", "POST", { refresh_token: rt }, false);
    if (!res.ok) return false;
    const j = await res.json();
    store.set({ access: j.access_token, refresh: j.refresh_token ?? rt });
    return true;
  }

  async function send(path: string, method = "GET", body?: unknown): Promise<Response> {
    let res = await raw(path, method, body);
    if (res.status === 401 && path !== "/auth/login") {
      if (await refresh()) res = await raw(path, method, body);
      else store.set({ access: null, refresh: null });
    }
    if (!res.ok) {
      const detail = await res.json().then((j) => j?.detail, () => undefined);
      throw new ApiError(res.status, typeof detail === "string" ? detail : res.statusText || "Request failed");
    }
    return res;
  }

  async function request<T>(path: string, method = "GET", body?: unknown): Promise<T> {
    const res = await send(path, method, body);
    return res.status === 204 ? (undefined as T) : res.json();
  }

  return {
    get: <T = unknown>(p: string) => request<T>(p),
    post: <T = unknown>(p: string, b?: unknown) => request<T>(p, "POST", b),
    patch: <T = unknown>(p: string, b?: unknown) => request<T>(p, "PATCH", b),
    put: <T = unknown>(p: string, b?: unknown) => request<T>(p, "PUT", b),
    del: <T = unknown>(p: string) => request<T>(p, "DELETE"),
    blob: async (p: string) => (await send(p)).blob(),
    async login(email: string, password: string) {
      const res = await raw("/auth/login", "POST", { email, password }, false);
      if (!res.ok) {
        const detail = await res.json().then((j) => j?.detail, () => undefined);
        throw new ApiError(res.status, typeof detail === "string" ? detail : "Sign-in failed");
      }
      const j = await res.json();
      store.set({ access: j.access_token, refresh: j.refresh_token });
    },
    logout() {
      const { refresh: rt } = store.get();
      store.set({ access: null, refresh: null });
      // Best effort: revokes the session server-side; the user is signed out locally either way.
      if (rt) void raw("/auth/logout", "POST", { refresh_token: rt }, false, true).catch(() => undefined);
    },
    hasSession: () => !!store.get().access,
  };
}

export const api = createApi({
  baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1",
  store: typeof window === "undefined" ? memoryStore() : browserStore(),
});
