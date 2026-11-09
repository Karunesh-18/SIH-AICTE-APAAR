"use client";
import { QueryClient, QueryClientProvider, useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useState, useSyncExternalStore, type ReactNode } from "react";
import { api } from "./api";
import type { Lang } from "./i18n";
import { t as translate } from "./i18n";
import { readLocalLang, subscribeLang, resolveLang, writeLocalLang } from "./lang";
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
  lang: Lang;
  setLang(l: Lang): void;
  t(key: string): string;
};
const AuthCtx = createContext<Ctx | null>(null);

const fetchMe = () => api.get<Me>("/auth/me");

function Inner({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const enabled = typeof window !== "undefined" && api.hasSession();
  const me = useQuery({ queryKey: ["me"], enabled, retry: false, staleTime: 60_000, queryFn: fetchMe });
  const user = me.isError ? null : (me.data ?? null);
  // Server snapshot is null, so server and first client render agree; the stored choice applies after hydration.
  const local = useSyncExternalStore(subscribeLang, readLocalLang, () => null);
  const lang = resolveLang(user?.language, local);
  useEffect(() => { document.documentElement.lang = lang; }, [lang]);
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
    lang,
    setLang(l) {
      writeLocalLang(l);
      if (user) {
        qc.setQueryData<Me>(["me"], { ...user, language: l });
        api.patch<Me>("/auth/me", { language: l }).catch(() => undefined); // choice still applies locally
      }
    },
    t: (key) => translate(lang, key),
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
