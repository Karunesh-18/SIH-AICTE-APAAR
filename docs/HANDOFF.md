# Handoff

Last updated: 2026-11-09.

Read this first, then `PROGRESS.md`. The full plan is in `PLAN.md`.

## Where things stand

- **Branches:** `phase-1-frontend` (login, API client, role-aware shell) and `phase-2-student-data` (student models, migration 0002, seed). Both are for PRs into `dev`. These docs do not record whether the PRs are open. Never commit to `main`.
- **Phase:** 1 (foundation). Backend done. Frontend login, API client and shell built. The browser check and the run check are still open.
- **Phase 2 (student data):** tables, migration `0002` and the synthetic seed are built. Ingestion and checks are Phase 3.
- **Verified:** 157 backend tests pass. 12 frontend tests pass (vitest). `next build` passes.
- **Not verified:** the frontend in a browser, in either theme. The Chrome extension was not connected, so no visual check was done.
- **Built in the frontend:** `/login` with demo-user buttons, the API client (one refresh and retry on 401), the auth context, the role-aware shell, en and hi text, and placeholder pages at `/aicte`, `/institution` and `/verifier`. The home page sends each role to its first route.
- **Built in the backend (Phase 1):** scaffold, JWT auth, the hash-chained audit log with verify, institutions API, the demo clock, notifications and the outbox, and CORS limited to `settings.cors_origins` (default `http://localhost:3000`). The list is in `API.md` ("Built").
- **Built in the backend (Phase 2):** tables `upload`, `student_record`, `validation_flag`, `flag_record`, `flag_event`, `registry_entry`, `rule` and `rule_version`. The seed writes 15 fictional institutions, 5 demo users, 12 rules at version 1, the mock registry and raw records for the demo cases. The seed writes no flags. Phase 3 raises them.

## Next steps (in order)

1. **Open the PRs into `dev`.** Use `gh pr create --base dev` for `phase-1-frontend` and for `phase-2-student-data`. Do not merge to `main`.
2. **Check the frontend in a browser.** Log in with each demo user, check the shell and the placeholder pages in both themes, and record the result. Until this is done, the frontend stays "built, not checked in a browser".
3. **Phase 3: ingestion and checks.** Write the failing tests first.
   - Parsers for CSV, XLSX, XLS and JSON. `openpyxl` and `xlrd` are in the install list.
   - Rules R01 to R07 on upload. R03 reads the `registry_entry` table (the mock).
   - Duplicate IDs in one file follow ADR-012: the first row stays current, later rows are held with `is_current` false.
   - The upload UI.
   - Done when the Kaveri file gives exactly 3 flags covering 8 distinct rows. The seed is built for this count (open question 3). The test checks the seed rows, not the flags, so Phase 3 must still raise the flags.
   - Read `frontend/node_modules/next/dist/docs/` before using a Next.js API (see `frontend/AGENTS.md`).

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

### Seed (synthetic demo data)

Migrate first, then seed. The seed needs the tables.

```powershell
cd backend
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m app.seed
```

- To use a database other than `backend/apaar.db`, set `DATABASE_URL` first, for example `$env:DATABASE_URL = "sqlite:///./demo.db"`. Set it for both commands.
- **One command for the whole demo:** `.\.venv\Scripts\python -m app.seed --demo` (after `alembic upgrade head`). It empties the database, seeds, runs the checks, adds the submission window, the verifiers and the consents, and resets the demo clock. Same result every time apart from ids and timestamps. Phase 7 added the end-to-end test `tests/test_e2e_demo_cases.py` (the ten cases through the HTTP API).
- A plain `app.seed` refuses a database that already has institutions. To empty every table and seed again, run `.\.venv\Scripts\python -m app.seed --reset`.
- The seed creates 15 fictional institutions, 5 demo users (`admin@`, `officer@`, `inst-admin@`, `staff@` and `verifier@demo.test`, password `Demo@1234`), 12 rules at version 1, the mock registry, and raw records for the demo cases from the idea doc. It writes no flags.
- Every seeded APAAR ID starts with `9999` (ADR-014).

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. The login page offers the five demo users. Set `NEXT_PUBLIC_DEMO=0` to hide them.

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

### Docker (not built, untested)

`docker compose up` is planned for Phase 7. `docker-compose.yml` is written but has not been run. See ADR-006.

## Known limits

These are recorded in `PROGRESS.md`. They are not fixed yet.

- The audit verify cannot detect deletion of the last rows, because nothing after them points back.
- Two concurrent audit appends give HTTP 500 (a unique-key violation with no retry). Add a retry before production.
- The login rate limit is per email, in memory, per process. It can lock out a known email for 5 minutes.
- Tests use bcrypt cost 4. Production default is 12.
- Tokens are kept in `localStorage`. Any script on the page can read them (ADR-013). The client keeps the same refresh token after a refresh.
- `.env.example` sets `NEXT_PUBLIC_API_URL` to `http://localhost:8000`. The client uses this value as its base URL, and its paths start at `/auth/...`, so the value must include `/api/v1`. Set it to `http://localhost:8000/api/v1`.

## Open questions

Each question says which phase it blocks.

| # | Question | Blocks |
|---|---|---|
| 1 | **R01 wording.** The idea doc says a missing ID is "returned to the institution to fix" and also "held as pending APAAR, not rejected". This repo treats it as a flag plus `pending_apaar` status. Confirm. | Phase 3 |
| 2 | **Hard stop.** `rule_version.hard_stop` exists in the plan. The idea doc says a hard stop is "AICTE's choice". The advisory rule says the platform never rejects. What does `hard_stop` do? A proposal: it only changes how the upload is shown. It never refuses data. | Phase 3 |
| 3 | **The 8-row count.** The plan says the Kaveri file gives "exactly 3 flags covering 8 rows". The idea doc's example has 6 excess rows, plus 2 rows for the duplicate ID, plus 1 row for the contradiction. That is 9 rows if none overlap. **Resolved.** Seed row 60 has an admission date in 2027. It sorts last by admission date, so it is one of the six over-cap rows. The flags then cover 6 (cap, including row 60) + 2 (duplicate rows 41 and 97) + 1 (future date, the same row 60) = 8 distinct rows. `test_kaveri_future_dated_row_is_among_the_six_over_cap_rows` in `backend/tests/test_seed.py` checks this. | Resolved (Phase 2 seed) |
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
| 21 | **Worked example arithmetic.** The idea doc says 3 flags cover 8 rows. Its parts are 6 (cap) + 2 (duplicate ID) + 1 (future date) = 9, unless one row sits in two flags. **Resolved.** Row 60 sits in the cap flag and in the future-date flag, as in question 3. The demo number 8 stands. | Resolved (Phase 2 seed) |
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
