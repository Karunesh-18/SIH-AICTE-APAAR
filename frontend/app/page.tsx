import { ThemeToggle } from "@/components/theme-toggle";
import { navFor } from "@/lib/nav";

// Phase 0 placeholder shell. Real landing page comes in Phase 7.
export default function Home() {
  const items = navFor("AICTE_OFFICER");
  return (
    <div className="flex min-h-screen">
      <aside className="flex w-60 flex-col border-r border-sidebar-border bg-sidebar p-4">
        <p className="font-semibold">Waymark APAAR Hub</p>
        <nav aria-label="Primary" className="mt-6 flex flex-1 flex-col gap-1 text-sm">
          {items.map((n) => (
            <span key={n.href} className="rounded-md px-3 py-2 text-sidebar-foreground">
              {n.key.replace("nav.", "")}
            </span>
          ))}
        </nav>
        <p className="text-xs text-muted-foreground">
          Prototype on synthetic data. Not an official AICTE system.
        </p>
      </aside>
      <main className="flex-1 p-8">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold">Scaffold running</h1>
          <ThemeToggle />
        </div>
        <p className="mt-3 max-w-prose text-muted-foreground">
          Nothing here is built yet beyond the shell, design tokens and the role-to-routes map.
        </p>
      </main>
    </div>
  );
}
