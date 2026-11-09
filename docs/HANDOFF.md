# Handoff

Last updated: 2026-11-09.

Read this first, then `PROGRESS.md`. The full plan is in `PLAN.md`.

## Where things stand

- **Branch:** `phase-0-setup`, cut from `dev`. Open the PR into `dev`. Never commit to `main`.
- **Phase:** 0 (setup), in progress.
- **Committed:** nothing from Phase 0 yet. At the start of the session `git status` showed `.gitignore`, `CLAUDE.md`, `backend/`, `docs/PLAN.md`, `frontend/` and `scripts/` as untracked.
- **Built:** project scaffold, `GET /health` endpoint with a test, a frontend scaffold with a tested nav map, design tokens, the test script (green), CLAUDE.md and the docs. Everything else is proposed.
- **Demo data:** none yet. The seed script is not written.

## What was done

- Backend: FastAPI app with `GET /health`. One test. `pyproject.toml` lists the runtime dependencies, plus pytest and httpx.
- Frontend: Next.js 16.4 with the App Router, Tailwind v4, shadcn/ui initialised (`components.json` present, no components added yet), TanStack Query and Table, Recharts, next-themes, qrcode.react and lucide-react. vitest is installed. npm scripts `test` and `gen:api` added.
- Design tokens: light and dark palettes in `frontend/app/globals.css`, with the theme provider and root layout in `frontend/app/layout.tsx`.
- `lib/nav.ts` maps each role to its routes. One test for it.
- `scripts/test.ps1` runs both suites and is green (backend 1 test, frontend 2 tests).
- `docker-compose.yml` written. Untested.
- Docs: the full set in `docs/` (ARCHITECTURE, DATA-MODEL, API, RULES, ROLES, GLOSSARY, DECISIONS, PROGRESS, HANDOFF).
- `docs/design.md` now matches the repo: the JWT login, audit log and registry rows are marked as proposed, rebuilt from Phase 1.
- `README.md` has the built-vs-proposed table and links to the docs.

## Next steps (in order)

1. **Write `.env.example`.**
2. **Replace the starter page with the shell.** Show the nav for a chosen role, in both themes. This is the Phase 0 "done when" check for the frontend. Read `frontend/node_modules/next/dist/docs/` first (see `frontend/AGENTS.md`).
3. **Commit and open the PR into `dev`.** Use `gh pr create --base dev`.
4. **Phase 1 (after Phase 0 is merged).** Write the failing tests first: the audit chain (clean, edited row, deleted row, fork rejected) and the role-scope tests. Add the first shadcn components with the shell. Then write the code.
5. **Check `README.md` against the repo** once the shell lands. `docs/design.md` is already updated.
6. **End of session.** Dispatch a Haiku subagent to update `PROGRESS.md` and `HANDOFF.md`, as CLAUDE.md requires.

## Open questions

Each question says which phase it blocks.

| # | Question | Blocks |
|---|---|---|
| 1 | **R01 wording.** The idea doc says a missing ID is "returned to the institution to fix" and also "held as pending APAAR, not rejected". This repo treats it as a flag plus `pending_apaar` status. Confirm. | Phase 3 |
| 2 | **Hard stop.** `rule_version.hard_stop` exists in the plan. The idea doc says a hard stop is "AICTE's choice". The advisory rule says the platform never rejects. What does `hard_stop` do? A proposal: it only changes how the upload is shown. It never refuses data. | Phase 3 |
| 3 | **The 8-row count.** The plan says the Kaveri file gives "exactly 3 flags covering 8 rows". The idea doc's example has 6 excess rows, plus 2 rows for the duplicate ID, plus 1 row for the contradiction. That is 9 rows if none overlap. The count is 8 only if one row is in two flags, and the rows counted are distinct. Confirm the test fixture. | Phase 3 |
| 4 | **Threshold values.** The plan does not set R08's similarity threshold, R10's percentage, R11's percentage, or R12's hours and category share. These are placeholders. | Phases 5 and 7 |
| 5 | **Audit genesis value.** The first entry of the chain needs a fixed `prev_hash`. The plan does not set one. | Phase 1 |
| 6 | **Verifier status values.** The plan uses `PENDING`. The other values (approved, rejected) are not written down. | Phase 6 |
| 7 | **Refused verification and the institution.** Does the institution learn about a refused request? The plan says the institution is notified about requests, but not about refusals. | Phase 6 |
| 8 | **Cross-institution alerts (R05) and privacy.** Should an institution see the other institution's name and the full APAAR ID in the alert? See `ROLES.md`. | Phase 3 |
| 9 | **Record transitions.** Whether `flagged` returns to `valid` when flags are resolved, and whether a `withdrawn` record can be restored. | Phase 4 |
| 10 | **Token key rotation.** What happens to tokens signed with an old key. | Phase 6 |
| 11 | **Registry access.** Can AICTE query the APAAR registry, under what authorisation, and what does a lookup return? This decides whether R03 can use real data. Until then it runs on the mock. (Idea doc section 32.) | Real-data use only |
| 12 | **Legal basis for consent.** When is consent needed, and when is a legitimate use enough? This sets the default consent behaviour. (Idea doc section 32.) | Phase 6 |
| 13 | **Mandatory fields per institution type.** (Idea doc section 32.) | Phase 3 |
| 14 | **Supernumerary seat categories and limits.** (Idea doc section 32.) | Phase 3 |
| 15 | **Transfers, breaks and repeats.** How they are recorded, so R05 does not raise alerts that everyone already understands. Cross-cycle checks are off by default. (Idea doc section 24.) | Phase 3 |
| 16 | **Submission windows per institution type,** and whether they repeat each year. (Idea doc section 32.) | Phase 5 |
| 17 | **Retention and removal.** How long records are kept, and who may ask for removal. (Idea doc section 32.) | Before any real data |
| 18 | **Verifier eligibility.** Which organisations may register, and who approves them. (Idea doc section 32.) | Phase 6 |
| 19 | **Certificate layouts.** Whether degree-awarding bodies will print the APAAR ID on certificates. This depends on them, not on this project. (Idea doc section 10.) | None in code |
| 20 | **Missing APAAR ID: returned or pending?** The idea doc says a missing ID is both "returned to the institution to fix" and "held as pending APAAR". RULES.md follows "pending". Confirm with the team. | Phase 3 |
| 21 | **Worked example arithmetic.** The idea doc says 3 flags cover 8 rows. Its parts are 6 (cap) + 2 (duplicate ID) + 1 (future date) = 9, unless one row sits in two flags. Decide which row overlaps, or fix the demo number. | Phase 2 (seed) |
| 22 | **Meaning of `rule_version.hard_stop`.** Under the advisory-only principle its effect is undefined. Decide what it does, or drop it. | Phase 3 |
| 23 | **R05 alert text.** The alert names the other institution, which may conflict with the masking rules. | Phase 4 |

## How to run

These commands are for Windows PowerShell, from the repo root `W:\CODE\SIH-AICTE-APAAR`.

### Backend

Python 3.11 is required (ADR-005).

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install fastapi "uvicorn[standard]" sqlalchemy alembic pydantic-settings pyjwt bcrypt cryptography apscheduler python-multipart openpyxl xlrd scikit-learn pytest httpx
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

The install line lists the runtime dependencies from `pyproject.toml`, plus `pytest` and `httpx`.

Check it: open http://127.0.0.1:8000/health. It should return `{"status": "ok"}`.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

Before using any Next.js API, read `frontend/node_modules/next/dist/docs/` (see `frontend/AGENTS.md`).

### Tests

```powershell
scripts\test.ps1
```

This runs `pytest -q` in `backend/` (using `backend\.venv`), then `npx vitest run` in `frontend/`. It exits with code 1 if either suite fails.

### Seed and demo (not built)

```powershell
cd backend
.\.venv\Scripts\python -m app.seed --reset
```

The seed is Phase 2. It does not exist yet.

### Docker (not built, untested)

`docker compose up` is planned for Phase 7. `docker-compose.yml` is written but has not been run. See ADR-006.

## Known deviations

| Deviation | Why | Where it is decided |
|---|---|---|
| History is kept in the same table as superseded rows. The idea doc has a separate history table. | Simpler writes, one transaction. | ADR-001 |
| Python 3.11 with pip, not `uv` with Python 3.12. | Neither `uv` nor Python 3.12 is installed. | ADR-005 |
| Docker Compose is not tested. | Docker is not installed on the dev machine. | ADR-006 |
| No code is copied from the earlier prototypes. | Clean history, no hidden secrets. | ADR-004 |
| The build order is the plan's phases 0 to 7. The idea doc's order (section 31) is older. | The plan was revised after the idea doc. | `PLAN.md` |
| R03 (registry lookup) is in Phase 3. The idea doc puts it in its sixth phase. | Plan order. | `PLAN.md` |
| Some API paths differ from the idea doc. | The plan set the names. | `API.md` |

## Files not to edit

- `submission/*`. Already submitted. The plan says these stay untouched.
- `docs/PLAN.md`. The approved plan.
- `CLAUDE.md`. Changes need the team's agreement.
