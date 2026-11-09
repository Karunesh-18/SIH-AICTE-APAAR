# Decisions

Last updated: 2026-11-09.

Each record below is an Architecture Decision Record (ADR). The format is:

- **Status:** Accepted, Superseded or Proposed.
- **Context:** why the decision was needed.
- **Decision:** what was decided.
- **Consequences:** what follows from it, good and bad.

Source for ADR-001 to ADR-006: `docs/PLAN.md` (settled decisions, grilling rounds 1 to 3). ADR-007 to ADR-011 come from Phase 1 build work. ADR-012 and ADR-014 come from Phase 2 build work. ADR-013 comes from the Phase 1 frontend.

## Index

| ADR | Title | Status |
|---|---|---|
| ADR-001 | History kept as superseded rows in `student_record` | Accepted |
| ADR-002 | No Verhoeff check by default. A `checksum` parameter is provided. | Accepted |
| ADR-003 | Ed25519 signed verification tokens | Accepted |
| ADR-004 | No code copied from earlier prototypes. Rebuilt from scratch. | Accepted |
| ADR-005 | Python 3.11 with venv and pip, not uv and Python 3.12 | Accepted (temporary) |
| ADR-006 | Docker Compose is written but untested, because Docker is not installed | Accepted |
| ADR-007 | A permission-matrix test lists every API route | Accepted |
| ADR-008 | The app refuses a default or short JWT secret outside demo mode | Accepted |
| ADR-009 | Email goes through a transactional outbox | Accepted |
| ADR-010 | Refused reads of out-of-scope records are audited | Accepted |
| ADR-011 | Migrations do not import app types | Accepted |
| ADR-012 | A duplicate ID in one file keeps the first row current | Accepted |
| ADR-013 | Tokens in localStorage for the prototype | Accepted (prototype only) |
| ADR-014 | Every seeded APAAR ID starts with 9999 | Accepted |

---

## ADR-001: History kept as superseded rows in `student_record`

**Status:** Accepted. Replaces the separate history table in the idea doc (section 17).

**Context.** A student record changes over time. An institution corrects a spelling, adds a late admission, or withdraws a student. AICTE needs the earlier version and when it was replaced. The idea doc proposed a `student_record_history` table. A separate table means two writes for every change and a second place to keep in step.

**Decision.** Keep superseded versions as rows in `student_record`. Each row has `is_current`, `superseded_at` and `superseded_by`. The partial unique index applies to current rows only: `(apaar_id, programme_id, cycle_year)` where `is_current` and `apaar_id` is not null.

**Consequences.**
- One write path. The record, its history and its audit entry are written in one transaction.
- Every query for current records must filter on `is_current`. Forgetting this gives wrong counts.
- The table grows with every correction. This is acceptable for the demo.
- The partial index works on both SQLite and Postgres.

---

## ADR-002: No Verhoeff check by default. A `checksum` parameter is provided.

**Status:** Accepted.

**Context.** The idea doc says the team has no information about a check digit on the APAAR ID, so it does not claim one. If a Verhoeff check were switched on and the check were wrong, valid IDs would be flagged. The rules must not claim a check that has not been confirmed.

**Decision.**
- R02 checks that the ID has 12 digits after spaces and hyphens are removed.
- R02 takes a `checksum` parameter: `none` or `verhoeff`. The default is `none`.
- `apaar.verhoeff_ok` is written so that the check can be switched on later.

**Consequences.**
- By default, R02 checks length and digits only.
- An AICTE decision to use a check digit is a parameter change, not a code change.
- The Verhoeff code needs its own tests before it is switched on.

---

## ADR-003: Ed25519 signed verification tokens

**Status:** Accepted.

**Context.** A verifier must be able to check that a result is genuine and was not changed. A printed or forwarded QR code must still be checkable later. The check must work offline from the token alone, except for expiry and revocation, which need the server.

**Decision.**
- Tokens are JWTs signed with Ed25519, using PyJWT (EdDSA) and `cryptography`.
- The public key is served at `GET /api/v1/verify/public-key`.
- The server still checks expiry and revocation. A valid signature alone is not enough.
- The signing key is generated on first run into `keys/`, which is gitignored. It can also be read from the environment.

**Consequences.**
- A token changed by one character fails the signature check. The plan's test for this must pass.
- No private key is in the repository. The repository is public.
- Key rotation is not defined. Tokens signed with an old key will need a plan.

---

## ADR-004: No code copied from earlier prototypes. Rebuilt from scratch.

**Status:** Accepted.

**Context.** The team has earlier work: a prototype called Waymark, and an older SIH repository. Some concepts (role guards, an audit chain, an obligation engine, a simulated clock) carry over. The repository is public. Copied code brings its own history, secrets and assumptions with it.

**Decision.** No code is copied from `W:/CODE/SIH-AICTE` or `W:/CODE/Waymark`. The concepts are rebuilt in this repository, with tests written first.

**Consequences.**
- More work in the early phases. Phase 1 rebuilds the audit chain and roles.
- Clean history and no hidden secrets.
- The earlier repositories are references for ideas only. Their docs can still describe what they did.

---

## ADR-005: Python 3.11 with venv and pip, not uv and Python 3.12

**Status:** Accepted (temporary). Review when Python 3.12 and uv are installed.

**Context.** The plan says `uv` and Python 3.12. Neither `uv` nor Python 3.12 is installed on the dev machine. The machine has Python 3.11.9.

**Decision.** Use a Python 3.11 venv at `backend/.venv` with pip. `backend/pyproject.toml` keeps `requires-python = ">=3.11"`.

**Consequences.**
- Setup uses plain pip. The commands are in `HANDOFF.md`.
- The lock file that `uv` would produce does not exist. Versions are not pinned yet.
- Moving to 3.12 later should need no code change, but this has not been tested.

---

## ADR-006: Docker Compose is written but untested, because Docker is not installed

**Status:** Accepted.

**Context.** The plan requires one `docker compose up` that is verified end to end. The dev machine does not have Docker installed.

**Decision.** Write `docker-compose.yml` and `.env.example` in Phase 7. Label the Docker path as untested in the README and the docs until it is run on a machine with Docker.

**Consequences.**
- Nobody can say the Docker path works until it has been run.
- The Phase 7 done-when criterion ("a `docker compose up` verified end to end") is not met until a machine with Docker runs it.

---

## ADR-007: A permission-matrix test lists every API route

**Status:** Accepted.

**Context.** Role checks are easy to forget on a new route. A missing check is a silent hole, and a review may not catch it.

**Decision.** `backend/tests/test_permission_matrix.py` is a table of routes against six callers: five roles and an anonymous user. A meta-test fails if any `/api/v1` route is not in the table.

**Consequences.**
- A new route cannot ship without a row saying who may call it.
- Every new route adds a row to the matrix. This is a small cost on each change.
- The matrix checks the role, not the object scope. Scope has its own tests (`test_access.py`).

---

## ADR-008: The app refuses a default or short JWT secret outside demo mode

**Status:** Accepted.

**Context.** The default JWT secret is in the repository. Anyone who knows it can sign tokens for any user.

**Decision.** `backend/app/core/config.py` raises an error at start-up when `DEMO_MODE` is off and `JWT_SECRET` is the default or has fewer than 32 characters. Demo mode keeps the default so a fresh clone runs.

**Consequences.**
- A deployment with a weak secret does not start. This is intended.
- Demo mode still accepts the default. Anyone who runs demo mode on a shared network is exposed.

---

## ADR-009: Email goes through a transactional outbox

**Status:** Accepted.

**Context.** Sending email inside a request can fail after the database change has been saved, or send an email for a change that was rolled back.

**Decision.** `services/notify.py` writes an `outbox` row in the same transaction as the change. `dispatch_queued` sends the rows after the commit. A row is tried up to 3 times (`MAX_ATTEMPTS`). Dispatch is idempotent: a sent row is not sent again.

**Consequences.**
- A sent email always matches a committed change.
- Dispatch runs in-process after commit. A crash between commit and dispatch leaves the row queued, and a later run sends it.
- Email is a console stub (`adapters/email.py`). No real provider is wired.

---

## ADR-010: Refused reads of out-of-scope records are audited

**Status:** Accepted.

**Context.** A user who asks for a record outside their scope may be probing. The officer needs to see those attempts.

**Decision.** When `GET /api/v1/institutions/{id}` refuses an out-of-scope institution, the refusal is written to the audit log as `ACCESS.REFUSED`, and the response is 403.

**Consequences.**
- Refusals show up in the audit log, so an officer can see probing.
- Only refusals are logged for the institution read. Successful reads and list reads are not audited. This differs from the plan's "single-record views are audited" line for records; that rule applies to the record routes, which are not built yet.

---

## ADR-011: Migrations do not import app types

**Status:** Accepted.

**Context.** A migration that imports `app.db.base.UTCDateTime` or a model class breaks when that code changes. Old migrations then stop running.

**Decision.** Migrations use plain SQLAlchemy column types only. A test checks that upgrade, downgrade and the models agree (`test_migrations.py`).

**Consequences.**
- Migrations stay runnable after model code changes.
- Each migration repeats some type details. This is a small cost.

---

## ADR-012: A duplicate ID in one file keeps the first row current

**Status:** Accepted.

**Context.** The database allows one current `student_record` per APAAR ID, programme and cycle (ADR-001, index `uq_record_current`). An upload can list the same ID twice. The idea doc says the platform accepts the data and flags it, and never rejects. If both rows were current, the second insert would fail.

**Decision.**
- The first row for an ID in a file stays current.
- Each later row for the same ID is stored with `is_current` false. It is kept, not dropped and not refused.
- Phase 3 ingestion must follow this. R04 raises the flag for the pair.
- The seed does this for the Kaveri case: row 41 is current, row 97 has `is_current` false.

**Consequences.**
- The database rule holds, and the platform still accepts the data.
- A held duplicate has no `superseded_at` or `superseded_by`. It was not replaced by a newer version, so it is not linked as history. Phase 3 should decide whether a held duplicate links to the current row.
- Queries for current records must filter on `is_current` (ADR-001).

---

## ADR-013: Tokens in localStorage for the prototype

**Status:** Accepted for the prototype only. Replace before any production use.

**Context.** The API issues a short-lived access token and a longer refresh token (JWT, HS256). The frontend runs on its own origin (`localhost:3000`) and the API on another (`localhost:8000`). A cookie set by the API is not sent from the frontend without a same-origin proxy. Cross-origin cookies also need CSRF handling. For a demo, keeping the tokens in the browser is the simplest working path.

**Decision.** `frontend/lib/api.ts` keeps both tokens in `localStorage` under one key (`waymark.session`). On a 401 the client calls `/auth/refresh` once and retries the request. If the refresh fails, it clears the stored session.

**Consequences.**
- Any script running on the page can read both tokens. A cross-site scripting bug gives an attacker both tokens.
- The client keeps the same refresh token after a refresh. A copied refresh token works until it expires (7 days by default, `refresh_days`).
- Upgrade path: serve the frontend and the API under one origin behind a proxy, and send the tokens in httpOnly cookies. Add CSRF protection for cookie-based requests.

---

## ADR-014: Every seeded APAAR ID starts with 9999

**Status:** Accepted.

**Context.** The repository is public and the demo data must not hold a real student's APAAR ID. The team does not hold the list of real IDs, so no check can rule a clash out. The seed makes a 12-digit ID for each student it creates, and the mock registry holds the same IDs.

**Decision.** Every seeded APAAR ID starts with `9999`, for example `999900001001`. Names are invented. `test_every_seeded_id_is_marked_invented_and_in_registry_with_matching_details` checks the prefix on every 12-digit seeded ID. The 11-digit ID in the Sahyadri case is cut from a seeded ID, so it also starts with `9999`.

**Consequences.**
- The prefix is a convention. It lowers the chance of a clash with a real ID but does not prove there is none.
- Nothing outside the seed enforces the prefix. Real data must never be loaded into the demo database.
- A real registry lookup needs authorisation first (open question 11). Until then R03 reads only the mock `registry_entry` table.

---

## ADR-015: A withdrawn record stays current but counts nowhere

**Status.** Accepted.

**Context.** Demo case 4: a student moves from Kaveri to Northfield mid-year. Kaveri withdraws its record. The platform must not block either institution, and history must stay.

**Decision.** `POST /records/{id}/withdraw` (reason required) sets `status = withdrawn` and `withdrawn_reason`. `is_current` stays true and `version` does not change, so the one-current-record index and the history are untouched. Withdrawn records are left out of R05 "active elsewhere" lookups (already in `validation._elsewhere`) and must be left out of intake and dashboard counts (Phase 5 reads this ADR). Withdrawing does not close any flag. The institutions holding an open R05 flag for the same student, and their region officers, are told, and an AICTE officer resolves the flag with a note. A withdrawn record cannot be corrected or withdrawn again (409). A later upload of the same student supersedes it like any current row.

**Consequences.**
- The system never decides that two institutions "agree"; the officer does, and the note is kept.
- Queries that count students must filter `status != 'withdrawn'` themselves.

---

## ADR-016: Review actions and record corrections

**Status.** Accepted.

**Decision.**
- The flag state machine is `domain/flags.py` (table-tested). Every action needs a note (422 without). A bad move is 409, a stale `lock_version` is 409, outside scope is 403 with an `ACCESS.REFUSED` audit entry. Institution roles can only read their own flags and `reply` to an ask. Officers and admins cannot reply.
- `link` exists for R08 (Phase 7). It resolves the flag and stores "Linked as the same student: ..." in the flag event. It does not change either record. It is 409 for any other rule.
- `PATCH /records/{id}` never edits a row. It marks the old row not current, adds version + 1 (`continues_record_id`, `superseded_by`), closes open flags of rules about one record's own fields (R01, R02, R03, R05, R07) with the event note "superseded by correction" (for R01 that gets its APAAR ID: a system note naming R01), carries R04, R06 and R08 flags over to the new version, and re-runs R01, R02, R03, R05 and R07 for that record. R04 and R06 are about a whole file and are not re-run per record. Nothing is rejected: if the new APAAR ID is already current in the same programme, the database would refuse it, so the call is 409 with a message.
- Editable fields: APAAR ID (cannot be cleared), name, date of birth, year of study, admission date, category, NRI, OCI, FN. The programme and cycle are fixed by the upload. Who: AICTE admin, or admin or staff of the record's own institution.
- Auto-closing is done "by the system" (no actor on the flag event); the audit entry names the user whose correction caused it.

---

## Other decisions in the plan (not ADRs)

These are settled in `docs/PLAN.md`. They are listed here so that they are easy to find.

- Demo-grade fidelity. SQLite by default. Production items are listed as not built.
- Students are not users in v1. Consent is recorded through the institution.
- Per-institution API keys: stored hashed, scoped to `records:submit`, revocable, every use audited.
- Public verifier registration creates a `PENDING` verifier. Only approved verifiers can send requests.
- Every rule change creates a new version. A revert creates a new version that copies an old one.
- Each flag records the rule version it was raised under.
- Purposes `EMPLOYMENT`, `HIGHER_EDUCATION`, `REGULATORY`, `SCHOLARSHIP`, each with an editable field allow-list.
- Background processing uses FastAPI `BackgroundTasks`, with the result page polling. Marked as in-process.
- Reminders use APScheduler, idempotent through a unique constraint.
- Tests are always written before code.
- Base platform scope: auth, audit chain, regions and registry, submission windows with reminders, a simulated clock, notifications and an outbox.
- English and Hindi from day one.
- Sober civic style. Light and dark themes.
- Deadline: none. Every phase is built. Nothing is cut.

---

## ADR-017: One metrics layer for dashboards and reports

**Status.** Accepted.

**Decision.** `services/metrics.py` is the only place that counts enrolment, flags and pending records. It counts current rows that are not withdrawn (ADR-015). A flag is open unless resolved or dismissed. Institution state: Excess when enrolment is above intake plus supernumerary or an R06 flag is open (so a closed R06 on an over-cap programme still shows Excess); Alert when other flags are open; Clear otherwise. A test checks that dashboard figures equal report figures. Reports are aggregate: no name, date of birth or APAAR ID; duplicate cases show only the ID masked when the flag was raised. Verifiers get no reports (403). Institution roles can only run reports for their own institution (another `institution_id` is 403 and audited). Every report run is audited as `REPORT.EXPORTED` (filters, format, row count).

---

## ADR-018: Window reminder ladder

**Status.** Accepted.

**Decision.** Ladder steps carry an audience (institution, officer, admin) and an offset in hours from `closes_at`. Defaults follow idea doc section 22: institution at 30, 14, 7 days before and on the day; officer 3 days after; admin 10 days after. Per audience only the latest due step is sent; earlier due steps are logged SKIPPED, so a clock jump never sends a burst. `run_cycle(db, now)` reads the demo clock, is idempotent (it reads the log and the unique key backs it), skips institutions that have submitted, and after `closes_at` lists non-submitters and raises R09 once per institution and cycle. APScheduler runs the cycle every `SCHEDULER_MINUTES` (15) only when `DEMO_MODE` is off or `SCHEDULER=1`; the admin button `POST /admin/windows/run-cycle` always works.

---

## ADR-019: Scheduled rules R09 to R12 (thresholds are placeholders)

**Status.** Accepted.

**Decision.** Pure functions in `domain/rules_scheduled.py`; `services/anomaly.py` raises flags (rule version snapshot, FlagEvent, audit, officer notice) and never raises an identical open flag (same institution, rule and cycle) twice. R10 compares with the previous cycle's current non-withdrawn count (no previous data, no flag). R12: one upload of at least `bulk_rows` rows in the last `last_hours` before close whose mix is unusual: one category above 80 percent, or a total-variation distance from the institution's earlier-cycle mix above 0.3. All numbers (`jump_pct` 25, `pending_pct` 20, `last_hours` 6, `bulk_rows` 50, 80 percent, 0.3) are placeholders for AICTE to set through the rule parameters.

