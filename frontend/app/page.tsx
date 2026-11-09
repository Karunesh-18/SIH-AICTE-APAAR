"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { homeFor } from "@/lib/nav";

// Placeholder entry. The public landing page comes in Phase 7; until then send people where they belong.
export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!loading) router.replace(user ? homeFor(user.role) : "/login");
  }, [user, loading, router]);
  return <main className="p-8 text-muted-foreground">Loading…</main>;
}
