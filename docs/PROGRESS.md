# Progress

Last updated: 2026-11-09.

Branch at the time of writing: `phase-0-setup`, cut from `dev`.

The phases come from `docs/PLAN.md`. Each phase is done when its "done when" line is true. Each phase goes through: branch off `dev`, tests first, code, review, PR into `dev`, then a docs update.

## Phase table

| Phase | Name | Status | Done when (from the plan) |
|---|---|---|---|
| 0 | Setup | **In progress** | `scripts/test.ps1` runs green on the empty suites. The frontend shows the shell in both themes. |
| 1 | Foundation | Not started | The audit tests (clean chain, edited row, deleted row, fork rejected) and the role-scope tests pass. |
| 2 | Student data | Not started | The seed runs on an empty DB. The DB rejects a duplicate current record. |
| 3 | Ingestion and checks | Not started | Every rule table passes. The Kaveri file gives exactly 3 flags covering 8 rows. |
| 4 | Review | Not started | A flagged record can be corrected through the UI. The history shows both versions. |
| 5 | Dashboards, reports, windows | Not started | Dashboard numbers equal report numbers on the seed. Advancing the clock produces reminders and the late list. |
| 6 | Consent and verification | Not started | Every refusal case refuses (no consent, expired, withdrawn, field outside scope, altered token, expired token). |
| 7 | R08 and polish | Not started | The Playwright demo runs all 10 cases from a fresh DB in one sitting. `docker compose up` is verified end to end. Then the `dev` to `main` PR. |

## Phase 0 checklist

Done (verified):

- [x] Backend skeleton: Python 3.11 venv with dependencies installed, including pytest, httpx and ruff. `backend/pyproject.toml` in place. `GET /health` in `backend/app/main.py`, with its test (`backend/tests/test_health.py`) written first.
- [x] Frontend scaffold: Next.js 16.4, App Router, Tailwind v4, TypeScript (`frontend/`). shadcn/ui init done, `frontend/components.json` in place. TanStack Query and TanStack Table, Recharts, next-themes, qrcode.react and lucide-react installed.
- [x] Test tooling: vitest and openapi-typescript installed properly. `@types/node` bumped to ^24 to resolve a peer conflict. An earlier `npx` run had hidden the missing install. npm scripts `test` and `gen:api` added.
- [x] Nav map: `frontend/lib/nav.ts` maps each role to its routes, with 2 tests in `frontend/lib/__tests__/nav.test.ts`.
- [x] `scripts/test.ps1` runs green: backend 1 test, frontend 2 tests.
- [x] `CLAUDE.md` written (untracked in git at the time of writing).
- [x] Docs set written: `ARCHITECTURE.md`, `DATA-MODEL.md`, `API.md`, `RULES.md`, `ROLES.md`, `GLOSSARY.md`, `DECISIONS.md`, `PROGRESS.md`, `HANDOFF.md`. `README.md` status table updated.
- [x] `docker-compose.yml` written. Untested: Docker is not installed on the dev machine (ADR-006).
- [x] `frontend/PRODUCT.md` written.
- [x] Design tokens: light and dark oklch palette, verdigris accent, Clear/Alert/Excess status colours, Geist and Noto Sans Devanagari fonts, theme provider and root layout in `frontend/app/globals.css` and `frontend/app/layout.tsx`.
- [x] Direction contract: `frontend/.impeccable/surfaces/app.md`.

Remaining in Phase 0:

- [ ] **`.env.example`.** Not written.
- [ ] **Shell.** `frontend/app/page.tsx` is still the create-next-app starter page. The Phase 0 "done when" line needs the shell in both themes, so this stays open until it is built.
- [ ] **Commit and PR.** Phase 0 changes are not committed. The PR goes into `dev`.
- [ ] **Model-routing preference saved to memory.** Not confirmed.

Deliberately deferred (not Phase 0 work):

- shadcn/ui components: add the first ones when the shell is built in Phase 1.
- `DESIGN.md`: written after real screens exist.
- Chart colours: provisional until the dataviz pass in Phase 5.
- Landing and verify pages: get their own Persuade design round in Phase 7.

## Phases 1 to 7

Not started. Scope is in `docs/PLAN.md` ("Phases" section). The idea doc's build order (section 31) is older. The plan's order is the one to follow.
