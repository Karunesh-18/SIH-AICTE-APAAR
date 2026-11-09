# Handoff

Last updated: 2026-11-09.

Read this first, then `PROGRESS.md`. The full plan is in `PLAN.md`.

## Where things stand

- **Branch:** `phase-1-foundation`. Open the PR into `dev`. Never commit to `main`.
- **Phase:** 1 (foundation). Backend done. Frontend login, API client and shell remain.
- **Verified:** 129 backend tests pass. Ruff is clean. 2 frontend tests pass.
- **Built in the backend:** scaffold, JWT auth, the hash-chained audit log with verify, institutions API, the demo clock, notifications and the outbox. Each has tests written first. The list is in `API.md` ("Built").
- **Not built in the frontend:** there is no login page and no API client. `frontend/app/page.tsx` is still the starter page.
- **Demo data:** none yet. The seed script is Phase 2.

## Next steps (in order)

1. **Open the PR `phase-1-foundation` into `dev`.** Use `gh pr create --base dev`. Do not merge to `main`.
2. **Frontend: login, API client and role-aware shell.** Build `frontend/app/login` against `POST /api/v1/auth/login`. Add `frontend/lib/api.ts` as the one API client. Wire the shell to `GET /api/v1/auth/me` and the nav map in `frontend/lib/nav.ts`. Add the first shadcn components with the shell. Show the shell in both themes. Read `frontend/node_modules/next/dist/docs/` first (see `frontend/AGENTS.md`).
3. **Then Phase 2 (student data).** Write the failing tests first: the seed runs on an empty DB, and the DB rejects a duplicate current record.

## How to run

These commands are for Windows PowerShell, from the repo root `W:\CODE\SIH-AICTE-APAAR`.

### Backend

Python 3.11 is required (ADR-005).

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install fastapi "uvicorn[standard]" sqlalchemy alembic pydantic-settings pyjwt bcrypt cryptography apscheduler python-multipart openpyxl xlrd scikit-learn pytest httpx ruff
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

The database is SQLite at `backend/apaar.db` by default. Run `alembic upgrade head` once before starting the server. Without it, the server starts, but the database calls fail.

To change settings, copy `.env.example` to `.env`. `DEMO_MODE=false` requires a `JWT_SECRET` of 32 or more characters that is not the default (ADR-008).

Check it: open http://127.0.0.1:8000/health. It should return `{"status": "ok"}`. API docs are at http://127.0.0.1:8000/docs.

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

Lint the backend with:

```powershell
cd backend
.\.venv\Scripts\python -m ruff check .
```

### Seed and demo (not built)

```powershell
cd backend
.\.venv\Scripts\python -m app.seed --reset
```

The seed is Phase 2. It does not exist yet.

### Docker (not built, untested)

`docker compose up` is planned for Phase 7. `docker-compose.yml` is written but has not been run. See ADR-006.

## Known limits

These are recorded in `PROGRESS.md`. They are not fixed yet.

- The audit verify cannot detect deletion of the last rows, because nothing after them points back.
- Two concurrent audit appends give HTTP 500 (a unique-key violation with no retry). Add a retry before production.
- The login rate limit is per email, in memory, per process. It can lock out a known email for 5 minutes.
- Tests use bcrypt cost 4. Production default is 12.

## Open questions

Each question says which phase it blocks.

| # | Question | Blocks |
|---|---|---|
| 1 | **R01 wording.** The idea doc says a missing ID is "returned to the institution to fix" and also "held as pending APAAR, not rejected". This repo treats it as a flag plus `pending_apaar` status. Confirm. | Phase 3 |
| 2 | **Hard stop.** `rule_version.hard_stop` exists in the plan. The idea doc says a hard stop is "AICTE's choice". The advisory rule says the platform never rejects. What does `hard_stop` do? A proposal: it only changes how the upload is shown. It never refuses data. | Phase 3 |
| 3 | **The 8-row count.** The plan says the Kaveri file gives "exactly 3 flags covering 8 rows". The idea doc's example has 6 excess rows, plus 2 rows for the duplicate ID, plus 1 row for the contradiction. That is 9 rows if none overlap. The count is 8 only if one row is in two flags, and the rows counted are distinct. Confirm the test fixture. | Phase 3 |
| 4 | **Threshold values.** The plan does not set R08's similarity threshold, R10's percentage, R11's percentage, or R12's hours and category share. These are placeholders. | Phases 5 and 7 |
| 5 | **Audit genesis value.** Answered in code: the first `prev_hash` is 64 zeros (`services/audit.py`). Confirm it is fine for the demo and record it in the plan. | Phase 1 (done in code) |
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

## Known deviations

| Deviation | Why | Where it is decided |
|---|---|---|
| History is kept in the same table as superseded rows. The idea doc has a separate history table. | Simpler writes, one transaction. | ADR-001 |
| Python 3.11 with pip, not `uv` with Python 3.12. | Neither `uv` nor Python 3.12 is installed. | ADR-005 |
| Docker Compose is not tested. | Docker is not installed on the dev machine. | ADR-006 |
| No code is copied from the earlier prototypes. | Clean history, no hidden secrets. | ADR-004 |
| The build order is the plan's phases 0 to 7. The idea doc's order (section 31) is older. | The plan was revised after the idea doc. | `PLAN.md` |
| R03 (registry lookup) is in Phase 3. The idea doc puts it in its sixth phase. | Plan order. | `PLAN.md` |
| Some API paths differ from the idea doc and from the plan. Built paths are under `/api/v1/admin/...` and `/api/v1/auth/me`. | The routes were written in Phase 1. | `API.md` |

## Files not to edit

- `submission/*`. Already submitted. The plan says these stay untouched.
- `docs/PLAN.md`. The approved plan.
- `CLAUDE.md`. Changes need the team's agreement.
