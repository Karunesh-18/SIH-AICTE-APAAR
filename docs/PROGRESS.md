# Progress

Last updated: 2026-11-10. Branch: `dev`.

All eight phases in `docs/PLAN.md` are built. The phases are delivered as a stack of pull requests. Each PR's base is the branch of the PR before it. Merge state is not recorded here.

## Checks

Run by the maintainer on 2026-11-09:

- Backend: 1003 tests pass.
- Frontend: 106 tests pass. `tsc`, `eslint` and `next build` are clean.
- Live smoke over HTTP (uvicorn and `next dev`, `python -m app.seed --demo`): every role's main endpoints return 200, and the main pages load. The audit chain verifies OK.

Not verified:

- A browser pass was done. Its findings were fixed in PR #16 and PR #17. Git does not record which screens it covered. Still unchecked: charts in both themes, dialogs, layout, the QR scan and Hindi on the new screens.
- Docker Compose is untested. Docker is not installed on the dev machine.
- Hindi strings for the new screens have no native-speaker review.

Known limits are listed in `HANDOFF.md`.

## Phase table

| Phase | Name | PR | Status | Done when (from the plan) |
|---|---|---|---|---|
| 0 | Setup | Not recorded | Built | `scripts/test.ps1` runs green. The shell shows in both themes (theme hydration fixed in PR #16; no full both-theme check recorded). |
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

## Merged to `dev` after the stack

Test counts in the Checks section are from 2026-11-09. They were not re-run for these PRs.

- PR #15: frontend critique fixes (brand lockup, type scale, Reports toolbar groups, i18n gaps, demo login buttons off by default, select theming).
- PR #16: browser-pass findings (theme hydration, nativeButton, Hindi gaps, select labels).
- PR #17: missing evidence labels (en, hi) for R07 to R12.
- PR #18: consent withdrawal names the student and purposes. Also the one-click launcher for non-technical teammates (commit `2f1a01c`).
- PR #20: refresh-token rotation with reuse detection (ADR-026).
- PR #21: SMTP email adapter behind the existing interface (ADR-027). Tested against a fake server only.
- PR #22: printable certificate record with a signed CERTIFICATE QR token (migration 0008).
- PR #24: refresh of the handoff, progress and design docs.
- PR #25: offline check of signed QR tokens on the public verify page (ADR-028). Unit tested. Not checked in a browser.
- PR #26: signed audit checkpoints that catch truncation of the last rows (ADR-029, migration 0009). Tested. No UI yet. The full backend suite was 1058 passed on the branch.
- PR #27: checkpoint UI on `/admin/audit`. Create checkpoint, the checkpoint outcome under verify, a demo-only Delete last 3 rows button with a confirm dialog, and a list of recent checkpoints with copy-token. Not checked in a browser.
- PR #28: impact preview for R08, R10 and R11 rule parameters (ADR-030). `POST /api/v1/admin/rules/{code}/preview` and a Preview impact button on the rule edit page. Nothing is saved. Full backend suite 1070 passed and frontend 141 passed on the branch. Not checked in a browser.

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
