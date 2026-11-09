"use client";
import { QueryClient, QueryClientProvider, useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useState, type ReactNode } from "react";
import { api } from "./api";
import type { Lang } from "./i18n";
import { t as translate } from "./i18n";
import type { Role } from "./nav";

export type Me = {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  institution_id: string | null;
  language: Lang;
};

type Ctx = {
  user: Me | null;
  loading: boolean;
  signIn(email: string, password: string): Promise<Me>;
  signOut(): void;
  t(key: string): string;
};
const AuthCtx = createContext<Ctx | null>(null);

const fetchMe = () => api.get<Me>("/auth/me");

function Inner({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const enabled = typeof window !== "undefined" && api.hasSession();
  const me = useQuery({ queryKey: ["me"], enabled, retry: false, staleTime: 60_000, queryFn: fetchMe });
  const user = me.isError ? null : (me.data ?? null);
  const value: Ctx = {
    user,
    loading: enabled && me.isPending,
    async signIn(email, password) {
      await api.login(email, password);
      return qc.fetchQuery({ queryKey: ["me"], queryFn: fetchMe });
    },
    signOut() {
      api.logout();
      qc.clear();
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- full reload drops all in-memory state
      window.location.assign("/login");
    },
    t: (key) => translate(user?.language ?? "en", key),
  };
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [client] = useState(() => new QueryClient());
  return (
    <QueryClientProvider client={client}>
      <Inner>{children}</Inner>
    </QueryClientProvider>
  );
}

export function useAuth(): Ctx {
  const c = useContext(AuthCtx);
  if (!c) throw new Error("useAuth outside AuthProvider");
  return c;
}
