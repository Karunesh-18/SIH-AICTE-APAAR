# Handoff

Last updated: 2026-11-09. Branch: `phase-7-frontend`.

Read this first, then `PROGRESS.md`. The full plan is in `PLAN.md`. Decisions are in `DECISIONS.md`.

## Current state

- All eight phases of `PLAN.md` are built. Phase status and PR numbers are in `PROGRESS.md`.
- Backend: 1003 tests pass. Frontend: 106 tests pass. `tsc`, `eslint` and `next build` are clean.
- Live smoke over HTTP with the demo seed: every role's main endpoints return 200, the main pages load, and the audit chain verifies OK.
- Built but not checked in a browser: every screen, both themes, charts, Hindi rendering, dialogs and the QR scan.
- Stubs: email and SMS write to the console. Real SMTP and SMS are not built.
- Not built: encryption at rest, a job queue, object storage, and a registry lookup against real data.
- Docker Compose is written but untested (Docker is not installed).

## How to run from scratch

Windows PowerShell, from the repo root `W:\CODE\SIH-AICTE-APAAR`. Needs Python 3.11 and Node.js 20.9 or later.

### Backend

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install fastapi "uvicorn[standard]" sqlalchemy alembic pydantic-settings pyjwt bcrypt cryptography apscheduler python-multipart openpyxl xlrd scikit-learn pytest httpx ruff xlwt
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m app.seed --demo
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

- No environment variables are needed. The database is SQLite at `backend/apaar.db`.
- `DEMO_MODE` is on by default, so the published demo JWT secret is accepted (ADR-008). To change settings, put them in `backend/.env` (see `.env.example` and `backend/app/core/config.py`).
- `app.seed --demo` empties the database and seeds it again, so it can be run again at any time.
- Check it: http://127.0.0.1:8000/health returns `{"status": "ok"}`. API docs are at http://127.0.0.1:8000/docs.

### Frontend

Open a second terminal.

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. The API defaults to `http://localhost:8000/api/v1`, so no variable is needed. Demo-user buttons on the login page are off by default; set `NEXT_PUBLIC_DEMO=1` (for example in `frontend/.env.local`, gitignored) to show them.

Before using any Next.js API, read the docs in `frontend/node_modules/next/dist/docs/`. This version of Next.js has breaking changes.

### Demo logins

Password for all of them: `Demo@1234`

| Email | Role |
|---|---|
| `admin@demo.test` | AICTE admin |
| `officer@demo.test` | AICTE officer |
| `inst-admin@demo.test` | Institution admin (Kaveri Valley College) |
| `staff@demo.test` | Institution staff |
| `verifier@demo.test` | Verifier, approved (seeded by `--demo`) |

### Tests and lint

```powershell
scripts\test.ps1
```

This runs pytest in `backend/` and vitest in `frontend/`. It exits with code 1 if either suite fails.

```powershell
cd backend
.\.venv\Scripts\python -m ruff check .
```

## Demo walk-through (about 10 minutes)

Run the backend and frontend as above, with `app.seed --demo` done. The steps below follow the ten cases in `submission/idea.txt` section 29. Logins are the demo users above.

| # | Case (idea doc section 29) | Where to show it | Login | What to point at |
|---|---|---|---|---|
| 1 | Clean upload: Malabar Pharmacy College, 40 students against intake 40 | `/institution` (submission status), upload receipt at `/institution/uploads/[id]`, `/aicte` (dashboard) | `inst-admin@`, then `admin@` | No flags. Malabar shows Clear on the dashboard. |
| 2 | Excess intake: Kaveri Valley College, 132 against 126 allowed | `/institution/uploads/[id]`, `/review`, `/review/[id]` | `inst-admin@`, `officer@` | The R06 flag shows 126 allowed, 132 actual, 6 excess. The officer dismisses the R04 duplicate with a note, and the R06 flag moves to under review. This differs from the idea doc (which dismisses two rows and leaves four open). The built test follows the version here. |
| 3 | Bad IDs: one 11-digit ID and one missing ID | `/institution/uploads/[id]` | `inst-admin@` | Each row shows its rule code and row number. The missing-ID record is held as pending APAAR. Nothing else in the file is held. |
| 4 | Same student at two institutions | `/review/[id]` (R05), `/notifications` | `officer@`, `inst-admin@` | Kaveri's users receive "Student listed elsewhere". Northfield has no demo users, so its side is shown through the data. Northfield withdraws its record (`/institution/records/[id]`). The officer resolves the flag with a note. |
| 5 | Student with no APAAR ID yet | `/institution/records` (filter `pending_apaar`), `/aicte` (pending share tile) | `staff@`, `admin@` | The record is held as `pending_apaar` and counted in its own figure. Adding the ID with a correction on `/institution/records/[id]` runs R01 again. |
| 6 | Near duplicate: similar names, same date of birth, different IDs | `/review/[id]` (R08) | `officer@` | The score, the threshold and the masked IDs are shown. The officer links the records or dismisses the flag. |
| 7 | Verification with consent | `/institution/consents` (record consent), `/verifier` (request), `/verify/[token]` (QR target) | `inst-admin@`, `verifier@` | The answer has three fields and a signed token. The QR code opens the check page. |
| 8 | Verification without consent, and after withdrawn consent | `/verifier` (generic answer), `/verifications` and `/admin/audit` (precise reason) | `verifier@`, `admin@` | The verifier sees only `CONSENT_NOT_AVAILABLE`. AICTE sees the precise reason, and `VERIFICATION.REFUSED` is in the log. |
| 9 | Tampering | `/admin/audit` (tamper button, then verify) | `admin@` | The tamper button edits one row (demo mode only). Verify reports the first broken row. |
| 10 | Clock past the window close | `/admin/clock`, `/admin/windows` (reminders and late list), `/reports` | `admin@` | Advancing the clock past close produces reminders, the late list and R09 flags. |

The same ten cases run as one automated test: `backend/tests/test_e2e_demo_cases.py`. It goes through the HTTP API, not the browser.

## Not verified

- No screen has been opened in a real browser. The Chrome extension was never connected. Layout, both themes, charts, dialogs, Hindi rendering and the QR scan are all unchecked.
- The walk-through above is written from the routes and the test. It has not been clicked through.
- Docker Compose has not been run. Docker is not installed.
- Hindi strings for the new screens have no native-speaker review.
- The scheduler thread has not run in tests. Tests cover only the on and off switch.
- Email and SMS are console stubs. No real provider is wired.
- Playwright was not used.

## Known limits

- Rate limits are in memory, per process. The login limit is per email. A known email can be locked out for 5 minutes.
- One Ed25519 signing key, with no rotation. It is not encrypted at rest. Replacing it invalidates every issued token (ADR-022).
- Access and refresh tokens are kept in `localStorage`, so any script on the page can read them (ADR-013). Refresh tokens rotate with reuse detection (ADR-026): a copied token stops working once the real client refreshes. A script that reads the current token can still use it until it is rotated or expires (7 days).
- No forced password change at first login (ADR-025).
- Audit verify cannot detect deletion of the last rows, because nothing after them points back. Two concurrent audit appends return HTTP 500, with no retry.
- R05 runs when a record arrives and when it is corrected (ADR-016). It does not run again when the other side changes. Withdrawing a record does not close the flag. Only an officer closes it.
- The R05 flag and its notification name the other institution. The APAAR ID in the flag is masked.
- R08 needs an exact date-of-birth match. The thresholds for R08, R10, R11 and R12 are placeholders for AICTE to set.
- The scheduler starts only when `DEMO_MODE` is off or `SCHEDULER=1` (ADR-018).
- Background processing and email dispatch run in the process, with no queue. One process is assumed.
- The frontend `DataTable` sorts the current page only. The audit page filters on the first 100 rows, on the client.
- `GET /api/v1/institutions/{id}/records` lists current records across all cycles. After `--demo` it also lists the 2025 rows seeded for R10.
- Tests run bcrypt at cost 4. The production default is 12.

## Open questions

| # | Question | Status |
|---|---|---|
| 1 | R01 wording. The idea doc says a missing ID is "returned to the institution" and also "held as pending APAAR". | Decided: a missing ID gets an R01 flag and status `pending_apaar`. Nothing is rejected. The "returned" wording is not followed. |
| 2 | Hard stop. What `rule_version.hard_stop` does. | Decided: display only. The field is stored per rule version, editable by the AICTE admin, and shown on the flag detail. No rule uses it to refuse, hold or change data. |
| 3 | The Kaveri count (3 flags covering 8 rows). | Resolved. Seed row 60 is both over the cap and dated in 2027. |
| 4 | Threshold values for R08, R10, R11 and R12. | Open. Placeholders. AICTE to set. |
| 5 | Audit genesis value. | Resolved in code: the first `prev_hash` is 64 zeros. Confirm for the record. |
| 6 | Verifier status values. | Decided in code: `PENDING`, `APPROVED`, `REJECTED`. |
| 7 | Does the institution learn about a refused request? | Decided in code: the institution is notified on a grant only (ADR-021). |
| 8 | R05 alert: should an institution see the other institution's name and the full APAAR ID? | Open. Code shows the other institution's name and programme, and masks the APAAR ID. The team has not confirmed this. |
| 9 | Record transitions: does `flagged` return to `valid`, and can a withdrawn record be restored? | Partly decided: a withdrawn record cannot be corrected or withdrawn again (409). Restore is not built. |
| 10 | Token key rotation. | Open. Not built. |
| 11 | Registry access: can AICTE query the APAAR registry, under what authority? | Open. R03 runs on the mock. |
| 12 | Legal basis for consent. When is consent needed, and when is a legitimate use enough? | Open. The code requires a consent record for every verification. The legal basis is not decided. |
| 13 | Mandatory fields per institution type. | Open. Not set. |
| 14 | Supernumerary seat categories and limits. | Open. |
| 15 | Transfers, breaks and repeats. Cross-cycle checks are off by default. | Open. |
| 16 | Submission windows per institution type, and whether they repeat yearly. | Open. |
| 17 | Retention and removal. | Open. Needed before any real data. |
| 18 | Verifier eligibility. | Open. Approval is per purpose, by the AICTE admin. Eligibility rules are not written down. |
| 19 | Certificate layouts. | Not a question for this project. |
| 20 | Missing APAAR ID: returned or pending? | Same as question 1. |
| 21 | Worked example arithmetic. | Resolved (same as question 3). |
| 22 | Meaning of `hard_stop`. | Same as question 2. |
| 23 | R05 alert text. | Same as question 8. |

## Known deviations

| Deviation | Why | Where it is decided |
|---|---|---|
| History is kept in the same table as superseded rows. The idea doc has a separate history table. | Simpler writes, one transaction. | ADR-001 |
| Python 3.11 with pip, not `uv` with Python 3.12. | Neither `uv` nor Python 3.12 is installed. | ADR-005 |
| Docker Compose is not tested. | Docker is not installed on the dev machine. | ADR-006 |
| No code is copied from the earlier prototypes. | Clean history, no hidden secrets. | ADR-004 |
| Build order follows the plan's phases 0 to 7. The idea doc's order (section 31) is older. | The plan was revised after the idea doc. | `PLAN.md` |
| Some API paths differ from the plan. Built paths are under `/api/v1/admin/...` and `/api/v1/auth/me`. | Routes were written in Phase 1. | `API.md` |
| Phase 7 "Playwright demo" is a pytest module through HTTP. | No browser run was done. | `PROGRESS.md` |

## Next steps (in order)

1. Browser pass of every screen, as each demo user, in light and dark themes and in Hindi. Record what breaks.
2. Visual check of the dashboard charts in both themes, against the validated palette.
3. Run `docker compose up` on a machine with Docker. Fix what fails. Until then, the Docker path stays "untested".
4. Replace the console stubs with real SMTP and SMS adapters behind the existing adapter interface. Not started.
5. Native-speaker review of the Hindi strings for the new screens.
6. Merge the stack in order, `#2` to `#14`, into `dev` (see `PROGRESS.md`). Then open the `dev` to `main` PR at this milestone.
7. Fix the known limits that matter before any real use: audit append retry, shared rate-limit storage, httpOnly cookies behind one origin, forced password change.

## Files not to edit

- `submission/*`. Already submitted.
- `docs/PLAN.md`. The approved plan.
