# Progress

Last updated: 2026-11-09.

Branch at the time of writing: `phase-1-foundation`.

The phases come from `docs/PLAN.md`. Each phase is done when its "done when" line is true. Each phase goes through: branch off `dev`, tests first, code, review, PR into `dev`, then a docs update.

## Phase table

| Phase | Name | Status | Done when (from the plan) |
|---|---|---|---|
| 0 | Setup | **In progress** | `scripts/test.ps1` runs green on the empty suites. The frontend shows the shell in both themes. |
| 1 | Foundation | **Backend done. Frontend login and shell remaining.** | The audit tests (clean chain, edited row, deleted row, fork rejected) and the role-scope tests pass. |
| 2 | Student data | Not started | The seed runs on an empty DB. The DB rejects a duplicate current record. |
| 3 | Ingestion and checks | Not started | Every rule table passes. The Kaveri file gives exactly 3 flags covering 8 rows. |
| 4 | Review | Not started | A flagged record can be corrected through the UI. The history shows both versions. |
| 5 | Dashboards, reports, windows | Not started | Dashboard numbers equal report numbers on the seed. Advancing the clock produces reminders and the late list. |
| 6 | Consent and verification | Not started | Every refusal case refuses (no consent, expired, withdrawn, field outside scope, altered token, expired token). |
| 7 | R08 and polish | Not started | The Playwright demo runs all 10 cases from a fresh DB in one sitting. `docker compose up` is verified end to end. Then the `dev` to `main` PR. |

## Phase 1 checklist

Done (verified by tests):

- [x] Config. `backend/app/core/config.py` refuses a default or short JWT secret when `DEMO_MODE` is off (ADR-008).
- [x] Clock. `backend/app/core/clock.py` gives `now()` with an offset. The offset is saved in `system_config` and restored at start-up.
- [x] Security. `backend/app/core/security.py` has bcrypt (cost from settings) and HS256 access and refresh JWTs with a `typ` claim.
- [x] Database base and session. One transaction per use case (`uow`).
- [x] Models: `region`, `institution`, `programme`, `user`, `user_region`, `audit_log`, `system_config`, `notification`, `outbox`. See `docs/DATA-MODEL.md`.
- [x] Alembic baseline migration `0001`. Tests check upgrade, downgrade, and that the migration matches the models.
- [x] Audit chain. `backend/app/services/audit.py` appends and verifies a SHA-256 chain from a genesis of 64 zeros. Tests cover a clean chain, an edited row, a deleted first or middle row, and a fork (rejected by the DB). Deleting the last rows is not detected (known limit).
- [x] Access rules. `backend/app/services/access.py` checks institution access and officer regions.
- [x] Clock admin. Advance or reset the clock. Audited as `CLOCK.SET`.
- [x] Notifications and outbox. `backend/app/services/notify.py` queues in the caller's transaction and sends after commit. Three attempts. Idempotent (ADR-009).
- [x] API. Login, refresh, `auth/me`, institutions (scoped), audit list and verify, tamper demo (demo mode only), clock, notifications. The built list is in `docs/API.md`.
- [x] Role-scope tests and the permission matrix. `backend/tests/test_permission_matrix.py` covers six callers and every route. A meta-test fails on any unlisted route (ADR-007).
- [x] Checks: 129 backend tests pass, ruff is clean.

Remaining in Phase 1:

- [ ] **Frontend login page.** No login page yet. `frontend/app/page.tsx` is still the starter page.
- [ ] **API client.** `frontend/lib/api.ts` does not exist yet.
- [ ] **Role-aware shell wired to real auth.** The shell is not built. The first shadcn components are added with it.
- [ ] **README and run check against a migrated DB.** The `uvicorn` run has not been checked after `alembic upgrade head`.

Known limits (recorded, not fixed):

- The audit verify cannot detect deletion of the last rows. Nothing after them points back to them.
- Two concurrent audit appends: the `UNIQUE(prev_hash)` rejects the second, which surfaces as HTTP 500. A retry is needed before production.
- The login rate limit is per email and in memory, per process. An attacker can lock a known email out for 5 minutes.
- Verify loads all audit rows. Fine for demo size.
- Tests use bcrypt cost 4 through a settings override. Production default is 12.

## Phase 0 checklist

Done (verified):

- [x] Backend skeleton: Python 3.11 venv with dependencies installed, including pytest, httpx and ruff. `backend/pyproject.toml` in place. `GET /health` in `backend/app/main.py`, with its test (`backend/tests/test_health.py`) written first.
- [x] Frontend scaffold: Next.js 16.4, App Router, Tailwind v4, TypeScript (`frontend/`). shadcn/ui init done, `frontend/components.json` in place. TanStack Query and TanStack Table, Recharts, next-themes, qrcode.react and lucide-react installed.
- [x] Test tooling: vitest and openapi-typescript installed properly. `@types/node` bumped to ^24 to resolve a peer conflict. An earlier `npx` run had hidden the missing install. npm scripts `test` and `gen:api` added.
- [x] Nav map: `frontend/lib/nav.ts` maps each role to its routes, with 2 tests in `frontend/lib/__tests__/nav.test.ts`.
- [x] `scripts/test.ps1` runs green: backend suite and frontend 2 tests.
- [x] `CLAUDE.md` written.
- [x] Docs set written: `ARCHITECTURE.md`, `DATA-MODEL.md`, `API.md`, `RULES.md`, `ROLES.md`, `GLOSSARY.md`, `DECISIONS.md`, `PROGRESS.md`, `HANDOFF.md`. `README.md` status table updated.
- [x] `docker-compose.yml` written. Untested: Docker is not installed on the dev machine (ADR-006).
- [x] `frontend/PRODUCT.md` written.
- [x] Design tokens: light and dark oklch palette, verdigris accent, Clear/Alert/Excess status colours, Geist and Noto Sans Devanagari fonts, theme provider and root layout in `frontend/app/globals.css` and `frontend/app/layout.tsx`.
- [x] Direction contract: `frontend/.impeccable/surfaces/app.md`.

Remaining in Phase 0:

- [ ] **`.env.example`.** Written in the repo, but the Phase 0 list still needs it checked against the code.
- [ ] **Shell.** The Phase 0 "done when" line needs the shell in both themes. This is folded into Phase 1 frontend work.
- [ ] **Commit and PR.** Not done. The PR goes into `dev`.
- [ ] **Model-routing preference saved to memory.** Not confirmed.

Deliberately deferred (not Phase 0 work):

- `DESIGN.md`: written after real screens exist.
- Chart colours: provisional until the dataviz pass in Phase 5.
- Landing and verify pages: get their own Persuade design round in Phase 7.

## Phases 2 to 7

Not started. Scope is in `docs/PLAN.md` ("Phases" section). The idea doc's build order (section 31) is older. The plan's order is the one to follow.
