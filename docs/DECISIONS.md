# Decisions

Last updated: 2026-11-09.

Each record below is an Architecture Decision Record (ADR). The format is:

- **Status:** Accepted, Superseded or Proposed.
- **Context:** why the decision was needed.
- **Decision:** what was decided.
- **Consequences:** what follows from it, good and bad.

Source for ADR-001 to ADR-006: `docs/PLAN.md` (settled decisions, grilling rounds 1 to 3). ADR-007 to ADR-011 come from Phase 1 build work.

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
