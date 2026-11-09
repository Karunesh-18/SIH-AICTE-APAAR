# Progress

Last updated: 2026-11-09 (browser pass partly done). Branch: `phase-7-frontend`.

All eight phases in `docs/PLAN.md` are built. The phases are delivered as a stack of pull requests. Each PR's base is the branch of the PR before it. Merge state is not recorded here.

## Checks

Run by the maintainer on 2026-11-09:

- Backend: 1003 tests pass.
- Frontend: 106 tests pass. `tsc`, `eslint` and `next build` are clean.
- Live smoke over HTTP (uvicorn and `next dev`, `python -m app.seed --demo`): every role's main endpoints return 200, and the main pages load. The audit chain verifies OK.

Not verified:

- Browser pass is partial (2026-11-09, Playwright on installed Chrome). Covered: all five demo roles, list screens in light and dark, Hindi on four admin screens, public pages, and mobile landing and login. Not yet checked: the QR scan, the valid-token verify page, dialogs and mutating flows, some detail pages, Hindi on institution and verifier screens, and a production build. Findings are in `HANDOFF.md`.
- Docker Compose is untested. Docker is not installed on the dev machine.
- Hindi strings for the new screens have no native-speaker review.

Known limits are listed in `HANDOFF.md`.

## Phase table

| Phase | Name | PR | Status | Done when (from the plan) |
|---|---|---|---|---|
| 0 | Setup | Not recorded | Built | `scripts/test.ps1` runs green. The shell shows in both themes (checked in the 2026-11-09 browser pass, with a dark-mode hydration issue on `/login`). |
| 1 | Foundation | #2 (backend), #3 (frontend shell) | Built | Audit tests and role-scope tests pass. |
| 2 | Student data | #4 | Built | The seed runs on an empty DB. The DB rejects a duplicate current record. |
| 3 | Ingestion and checks | #5, #6 | Built | Rule tables pass. The Kaveri file gives 3 flags covering 8 rows. |
| 4 | Review | #7, #8 | Built | A flagged record is corrected through the UI. History shows both versions. |
| 5 | Dashboards, reports, windows | #9, #10 | Built | Dashboard numbers equal report numbers on the seed. The clock produces reminders and the late list. |
| 6 | Consent and verification | #11, #12 | Built | Every refusal case refuses (no consent, expired, withdrawn, field outside scope, altered token, expired token). |
| 7 | R08 and polish | #13, #14 | Built, with gaps | The ten demo cases run from a fresh DB in one sitting. `docker compose up` verified. |

Phase 7 notes:

- The ten demo cases run as one pytest module, `backend/tests/test_e2e_demo_cases.py`, through the HTTP API. They do not run in a browser. Playwright was not used.
- `docker compose up` has not been run. It stays untested until a machine with Docker runs it (ADR-006).
- The `dev` to `main` PR is still to be opened at this milestone.

## Stacked PRs

Order, from the base branch (`dev`) upward:

`#2` → `#3` → `#4` → `#5` → `#6` → `#7` → `#8` → `#9` → `#10` → `#11` → `#12` → `#13` → `#14`

Each PR's base is the branch of the PR before it. To merge:

1. Merge `#2` into `dev`.
2. Retarget `#3` to `dev`, then merge it. Repeat in order up to `#14`.
3. Alternatively, if the last branch contains the whole stack, retarget `#14` to `dev` and merge it once.
4. After the stack is in `dev`, open the `dev` to `main` PR.

## Tests

- Backend: `backend/tests/`, run by `scripts\test.ps1` (pytest).
- Frontend: `frontend/**/__tests__/` and `frontend/components/__tests__/`, run by vitest.
