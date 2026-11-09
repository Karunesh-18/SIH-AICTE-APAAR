# Waymark APAAR Hub: frontend

Next.js 16 (App Router), TypeScript, Tailwind v4, shadcn/ui, TanStack Query and Table, Recharts. Prototype on synthetic data; not an official AICTE system. The API is the FastAPI app in `../backend`.

Next 16 differs from older versions. Read `node_modules/next/dist/docs/` before using a Next API.

## Run

```
cd frontend
npm install
npm run dev        # http://localhost:3000, expects the API on http://localhost:8000
```

Start the backend first (`cd backend; .\.venv\Scripts\python -m uvicorn app.main:app --reload`). For demo accounts run `python -m app.seed --demo` there; the login page lists them.

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | API base URL |
| `NEXT_PUBLIC_DEMO` | on | Set to `0` to hide the demo-account buttons on the login page |

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Dev server |
| `npm run build` / `npm start` | Production build and server |
| `npm test` | Vitest (pure logic and a few components) |
| `npx tsc --noEmit` | Type check |
| `npm run lint` | ESLint |
| `npm run gen:api` | Regenerate OpenAPI types (needs a running server; response types are otherwise hand-written in `lib/types.ts`) |

## Structure

- `app/` routes. `app/page.tsx` is the public landing page; `app/(app)/` is the signed-in shell (role-scoped nav); `app/verify/` and `app/verifiers/register/` are public.
- `components/` shared UI. `components/ui/` is shadcn.
- `lib/` pure logic with tests in `lib/__tests__/`: API client with token refresh (`api.ts`), auth and language context (`auth.tsx`, `lang.ts`), role navigation (`nav.ts`), i18n (`i18n/en.json`, `i18n/hi.json`).
- `.impeccable/surfaces/` design briefs; `PRODUCT.md` is the product and brand contract.

## Notes

- Strings go through `t()`; English and Hindi keys must match (a test enforces it, and another checks every literal key exists). The language choice is saved to the account for signed-in users and to `localStorage` on public pages.
- Authorisation is enforced by the server. The UI hides things for convenience only.
- Nothing here has been checked in a real browser by automated tooling; see `../docs/HANDOFF.md` for what is verified.
