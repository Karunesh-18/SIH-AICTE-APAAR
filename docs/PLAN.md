# Plan: Waymark APAAR Hub, the full build (SIH 26263)

## Context
This repo (`Karunesh-18/SIH-AICTE-APAAR`, public, branches `main` and `origin/dev`) holds only the deck, the README, `docs/design.md` and `submission/{title,abstract,idea}.txt`. The idea doc has 406 lines covering rules R01–R12, the data model, the API, roles, 10 demo cases and the build phases. There is no code yet. The deadline has moved, so the team is rebuilding the whole platform for problem statement SIH 26263 **from scratch in this repo**. Nothing is copied from `W:/CODE/SIH-AICTE` or `W:/CODE/Waymark`. The result should be a demo-grade platform that runs all 10 demo cases (§29 of the idea doc) on a fresh database on one laptop. The schema stays Postgres-compatible, SQLite is the default, and production items (encryption at rest, a queue, object storage) are listed as "not built".

## Settled decisions (grilling rounds 1–3)
| # | Decision |
|---|---|
| Fidelity | Demo-grade. SQLite by default with a Postgres-compatible schema. Production items documented as not built. |
| Code | New code in this repo only. `backend/` and `frontend/`. |
| Deadline | None for now. Build every phase, nothing cut. |
| Student fields | `name` and `dob` added. Masked by default; unmasked only for the record's own institution and for AICTE officers and admins. |
| Upload formats | CSV (UTF-8, BOM-tolerant), XLSX (openpyxl), legacy XLS (xlrd), JSON. One parser feeds one rule pipeline. Templates downloadable as CSV and XLSX. |
| Processing | FastAPI `BackgroundTasks`, with the result page polling. Marked `# ponytail: in-process, move to a queue at scale`. |
| Signed results | Ed25519 JWT (PyJWT EdDSA plus `cryptography`). Public key served at `GET /verify/public-key`. The server also checks expiry and revocation. |
| Students | Not users in v1. Consent is recorded through the institution. |
| Run | Local first (`uvicorn` and `next dev`, seeded SQLite), plus one `docker compose up` that is actually tested. |
| R02 | 12 numeric digits after stripping spaces and hyphens. A `checksum: none\|verhoeff` parameter is available, set to `none` by default, because no check digit has been confirmed. |
| Base scope | Rebuild only what the APAAR flows use: auth, the audit chain, regions and the registry, **submission windows** with a reminder ladder, a simulated clock, notifications and an outbox. |
| Docs | Rewrite all docs and add system-design and handoff docs. `submission/*.txt` stays untouched, since it was already submitted. |
| Roles | `AICTE_ADMIN`, `AICTE_OFFICER` (scoped to regions), `INSTITUTION_ADMIN`, `INSTITUTION_STAFF`, `VERIFIER`. |
| ERP auth | Per-institution API keys: stored hashed, scoped to `records:submit`, revocable, every use audited. |
| Verifiers | Public registration creates a `PENDING` verifier. An admin approves or rejects with a note. Only approved verifiers can send requests. |
| Data | All mock: fictional institutions, students and registry. A `RegistryAdapter` with `MockRegistry`. |
| Public pages | Landing page, `/verify/[token]`, `/verifiers/register`. |
| UI libraries | shadcn/ui (Radix) and Recharts in the app. On public pages, a few copy-in pieces from Magic UI, Aceternity or React Bits, Lenis smooth scroll, and at most one ShaderGradient hero. Inspiration only: Awwwards, Godly, Mobbin, Refero. No MUI, Chakra, Mantine, HeroUI, daisyUI, Flowbite, Barba, Spline or Unicorn. |
| Look | Sober civic/regulatory style, designed with impeccable. Charts must be clear (dataviz skill). Light and dark themes. en and hi from day one. |
| Rules admin | Every rule change creates a new version. Each flag snapshots the `rule_version_id` it was raised under. Diff and **revert** work like version control (a revert creates a new version that copies an old one). |
| Audit scope | Every write, every view of a single record, every export, every verification and every refusal. List and dashboard reads are not audited. |
| Consent | Purposes `EMPLOYMENT`, `HIGHER_EDUCATION`, `REGULATORY`, `SCHOLARSHIP`, each with an admin-editable field allow-list. A request outside the consent or the allow-list is refused. |
| Testing | **Tests are always written before code.** Table-driven pytest per rule, a role × endpoint permission matrix, a Playwright run of the 10 demo cases. |
| Models | Opus plans; Sonnet subagents implement; Haiku subagents update docs and handle small, easy tasks. |
| Git | Check out `dev` from `origin/dev`. For each feature or fix: branch off `dev` → PR into `dev` → `dev` → `main` PR at milestones. |

## Repo layout
```
backend/   pyproject.toml (uv), alembic.ini, migrations/, app/, tests/
frontend/  Next.js (latest stable, App Router), TS, Tailwind v4, shadcn/ui
docs/      ARCHITECTURE, DATA-MODEL, API, RULES, ROLES, GLOSSARY, DECISIONS (ADRs), PROGRESS, HANDOFF, DEMO
CLAUDE.md  agent operating manual + handoff protocol
docker-compose.yml, .env.example, scripts/dev.ps1, scripts/test.ps1
```

## Backend design (FastAPI, Pydantic v2 `extra="forbid"`, SQLAlchemy 2, Alembic, Python 3.12)
Layers: `api → services → domain (pure, no framework imports) → adapters`. One transaction per use case through a `uow(db)` context manager that writes the record, its history and the audit entry together.

**app/core**
- `config.py`: pydantic-settings.
- `clock.py`: `now()` with an offset persisted in `system_config`.
- `security.py`: bcrypt; HS256 access and refresh JWTs.
- `signing.py`: an Ed25519 key, generated on first run into a gitignored `keys/` folder or read from env.

**app/domain** (pure functions; all of these are TDD targets)
- `apaar.py`: `normalize(id)`, `check_format(id, checksum)`, `mask(id)` (→ `XXXX XXXX 1234`), `verhoeff_ok`.
- `rules/`: one function per rule, R01–R12, each `(input, params) -> list[FlagDraft{rule, reason_key, evidence, record_refs}]`.
- `intake.py`: allowed = intake + supernumerary; excess rows = the last N by admission date. The evidence notes that this is "only an ordering".
- `similarity.py`: scikit-learn TF-IDF over character n-grams (2–4) with cosine similarity, used by R08 and by the loose name match in R03.
- `ladder.py`: which reminder steps fire. Only the latest due step fires; earlier ones are logged as SKIPPED, never sent late in a burst.
- `consent.py`: `decide(request, consents, policy, now) -> Allow(fields) | Refuse(reason)`.
- `masking.py`: `serialize_record(record, viewer) -> dict`. Masking happens on the server per role and scope.
- `status.py`: record state machine (submitted → valid | flagged | pending_apaar | withdrawn).

**app/adapters**
- `registry.py`: `RegistryAdapter` Protocol and `MockRegistry`, backed by a seeded `registry_entry` table.
- `email.py`: `ConsoleEmail`.
- `sms.py`: `StubSms`, which writes to the database.

**app/services**
- `ingest.py`: format sniffing, then CSV, XLSX, XLS or JSON rows, then normalised rows. A file that can't be read, or is missing columns, is rejected whole. Otherwise good rows are accepted and the rest flagged. A `file_hash` match means a duplicate upload, which creates new versions rather than copies.
- `validation.py`: loads the active rule versions, runs the domain rules, writes flags, updates record status, and records notifications in the outbox.
- `records.py`: versioning (the current row plus superseded rows), withdraw, view (audited), and re-running checks when an APAAR ID is added.
- `review.py`: flag state changes (open / under_review / resolved / dismissed / ask_institution), each needing a note. The R08 link and dismiss actions live here too.
- `rules_admin.py`: rule versions, diff and revert.
- `windows.py`: submission windows and the reminder cycle, run by APScheduler and idempotent through UNIQUE(window, institution, step).
- `anomaly.py`: R09–R12 on a schedule.
- `dashboards.py` and `reports.py`: both read the same queries, so the numbers match. Reports export to CSV, report definitions can be saved, every export is audited, and outside-reader reports leave out identity fields.
- `consent.py`, `verifiers.py`, `verification.py`: the request is consent-checked, the response is limited to the allowed fields, the result is a signed token, and the institution is notified. Refusals are logged.
- `audit.py`: `append()` (SHA-256 of prev_hash plus canonical JSON; a DB UNIQUE on `prev_hash` prevents forks), `verify()` (returns the first broken id), and a tamper endpoint in demo mode only.
- `notify.py`: transactional outbox, then a dispatcher that runs after commit.
- `apikeys.py`

**Data model** (UUID PKs; `created_at` and `updated_at`; `version_id_col` on `student_record` and `validation_flag` for optimistic locking)
- `region`; `institution` (aicte_id, name, type, region_id, status).
- `programme` (institution, name, level, cycle_year, duration_years, approved_intake, supernumerary_seats). Read-only for institutions.
- `user` (role, institution_id); `user_region` (officer ↔ regions); `api_key` (hash, prefix, scopes, revoked_at).
- `upload` (institution, cycle, source, format, file_hash, row_count, status, accepted/flagged counts, uploaded_by).
- `student_record` (apaar_id nullable, name, dob, programme_id, cycle_year, year_of_study, admission_date, admission_category, nri, oci, fn, status, version, is_current, superseded_at/by, withdrawn_reason, continues_record_id, consent_ref, upload_id).
  - **Partial unique index** on (apaar_id, programme_id, cycle_year) WHERE is_current AND apaar_id IS NOT NULL. Works in both SQLite and Postgres.
  - History is kept as superseded rows in this same table rather than a separate history table. That is ADR-001.
- `validation_flag` (rule_code, rule_version_id, upload_id, reason_key, rendered reason, evidence JSON, state, assignee); `flag_record` (M:N); `flag_event` (from_state, to_state, actor, note, at).
- `rule` (code, scope `upload|cross|scheduled`); `rule_version` (rule_code, version_no, enabled, params JSON, hard_stop, message_en, message_hi, created_by, note, is_active).
- `registry_entry` (mock: apaar_id, name, dob).
- `consent` (apaar_id, purposes[], fields[], source, given_at, expires_at, withdrawn_at, recorded_by); `purpose_policy` (purpose, allowed_fields[], version).
- `verifier` (org, type, contact, requested_purposes, status, decided_by, decision_note); verifier users link to a verifier row.
- `verification_request` (verifier, apaar_id, purpose, fields_requested, consent_id, outcome, refusal_reason, token_jti, expires_at, revoked_at).
- `submission_window` (cycle_year, institution_type, opens_at, closes_at, ladder JSON); `window_alert_log` UNIQUE(window, institution, step).
- `notification`, `outbox`, `audit_log` (int id, prev_hash UNIQUE, hash), `system_config`, `saved_report`.

**API** (`/api/v1`; every route checks role and object scope; unknown fields are rejected; OpenAPI docs)
- auth: login, refresh, me, me PATCH (language).
- uploads: `POST /uploads` (multipart) → receipt; `GET /uploads/{id}`; `GET /templates/{csv|xlsx}`; `POST /institutions/{id}/students` (JWT or API key).
- records: `GET /institutions/{id}/records`, `GET /records/{id}` (audited, includes history), `POST /records/{id}/withdraw`, `PATCH /records/{id}` (correction → new version).
- flags: `GET /flags?state&rule&institution&region&age`, `GET /flags/{id}`, `POST /flags/{id}/{review|resolve|dismiss|ask|link}` (note required).
- dashboards: `/dashboards/aicte`, `/dashboards/institution`, `/dashboards/intake-use`.
- reports: `GET /reports`, `POST /reports` (save), `GET /reports/{name}?format=csv`.
- consent: `POST /consents`, `DELETE /consents/{id}`, `GET /consents?apaar`.
- verifiers: `POST /verifiers/register` (public), `POST /admin/verifiers/{id}/{approve|reject}`.
- verification: `POST /verifications`, `GET /verifications/{id}`, `GET /verifications` (scoped), `GET /verify/{token}` (public), `GET /verify/public-key`.
- admin: rules list, rule versions, rule PUT (creates a new version), diff, revert; purpose policies; users, regions, windows, clock, alert-cycle run, `GET /audit`, `POST /audit/verify`, `POST /dev/tamper-audit` (demo mode only).
- institution: api-keys CRUD, staff CRUD.

**Seed** (`python -m app.seed --reset`): regions, about 15 fictional institutions including Kaveri Valley, Northfield and Malabar Pharmacy, programmes, one user per role (`*@demo.test`), the mock registry, a submission window, purpose policies, rule v1 rows, and the data for each of the 10 demo cases.

## Frontend design (Next.js App Router, TS, Tailwind v4, shadcn/ui, TanStack Query and Table, Recharts through shadcn charts, `qrcode.react`, `next-themes`, Lenis on public pages only)
- `lib/api.ts`: a typed client generated with `openapi-typescript`, with one transparent refresh on 401.
- `lib/auth.tsx`: role-aware context.
- `lib/i18n/{en,hi}.json` and `t()`.
- `lib/nav.ts`: role → routes.
- Every screen has empty, loading and error states.

Routes:
- **Public:** `/` (landing), `/login` (with demo-account buttons), `/verify/[token]` (genuine / expired / revoked / tampered), `/verifiers/register`.
- **AICTE:**
  - `/aicte`: six tiles, the institution table (Clear/Alert/Excess), filters, and an intake-use chart.
  - `/aicte/institutions/[id]`: programme bars against the cap, flags, submission history.
  - `/review` and `/review/[id]`: reason, evidence, involved rows, and actions that require a note.
  - `/reports`, `/verifications`.
  - `/admin/rules` (versions, diff, revert), `/admin/policies`, `/admin/verifiers`, `/admin/users`, `/admin/windows`, `/admin/audit` (verify the chain plus the tamper demo), `/admin/clock`.
- **Institution:**
  - `/institution`: window status, accepted and flagged counts, to-do list.
  - `/institution/upload` (dropzone and format picker) → `/institution/uploads/[id]` (polling result).
  - `/institution/records` and `[id]` (with history).
  - `/institution/flags`, `/institution/consents`, `/institution/verifications`, `/institution/api-keys`, `/institution/staff`.
- **Verifier:** `/verifier` (request form, my requests, result with QR).
- **Shared:** `/notifications` (bell polls).

## Skills used per phase (from the skill scan)
| When | Skill |
|---|---|
| Plan each phase | `superpowers:writing-plans`, `codebase-design` (deep modules), `domain-modeling` (GLOSSARY and ADRs) |
| Implement | `superpowers:subagent-driven-development` (Sonnet), `superpowers:test-driven-development` / `tdd` (tests first, always) |
| UI direction and build | `impeccable:impeccable` (direction, tokens, critique), `frontend-design`, `dataviz` (every chart), `accessibility` |
| Security-sensitive phases (auth, consent, verification, API keys) | `security-review` / `cso` |
| Before a PR | `superpowers:verification-before-completion`, `code-review`, `ponytail-review`, `pr` (PR body) |
| End-to-end check | `qa` / `browse` (Playwright demo run) |
| Docs | Haiku subagent; `humanizer` to keep the plain voice the team already uses |

## Phases (each one: branch off `dev` → tests → code → review → PR into `dev` → Haiku doc update)
0. **Setup.** Check out `dev`. Commit the current working-tree changes on `dev` (the renamed PDF and the untracked `submission/` folder). Scaffold the backend and frontend. Write `CLAUDE.md` and the docs skeleton plus HANDOFF. Run the impeccable direction pass and set the design tokens. Save the model-routing preference to memory. *Done when:* `scripts/test.ps1` runs green on empty suites and the frontend shows the shell in both themes.
1. **Foundation.** Auth, roles, regions, institutions and programmes, user_region scoping, the audit chain with verify and tamper, the clock, notifications and outbox, the permission-matrix test harness. *Done when:* the audit tests (clean, edited row, deleted row, fork rejected) and the role-scope tests pass.
2. **Student data.** The student, upload, flag, rule and registry tables, migrations, the seed for all 10 cases, constraint tests. *Done when:* the seed runs on an empty DB and a duplicate current record is rejected by the DB.
3. **Ingestion and checks.** Parsers for all four formats (edge cases: BOM, trailing spaces, Devanagari, day-first dates, empty file, extra columns, the same file twice), R01–R07 including R03 against MockRegistry, rule versions with revert, the API-key endpoint, the upload UI and result page. *Done when:* every rule table passes and the Kaveri file gives **exactly 3 flags covering 8 rows**.
4. **Review.** The queue, flag actions with notes, record corrections and versions, withdraw, re-running checks when an ID is added, the institution flag views. *Done when:* a flagged record can be corrected through the UI and the history shows both versions.
5. **Dashboards, reports, windows.** AICTE and institution dashboards, intake-use charts, saved reports and CSV, the submission-window ladder, R09–R12 on a schedule, the clock UI. *Done when:* dashboard numbers equal report numbers on the seed, and advancing the clock produces the reminders and the late list.
6. **Consent and verification.** Consent ledger, purpose policies, verifier registration and approval, verification requests, Ed25519 tokens, QR, the public verify page, institution notices. *Done when:* every refusal case refuses (no consent, expired, withdrawn, field outside scope, a token altered by one character, an expired token).
7. **R08 and polish.** TF-IDF near-duplicates, the full Hindi strings, the landing page visuals, a final impeccable critique, a `docker compose up` verified end to end, the final docs. *Done when:* the Playwright demo runs all 10 cases from a fresh DB in one sitting. Then the `dev` → `main` PR.

Each phase updates `README.md` and `docs/design.md` (built vs. proposed) to match reality.

## Docs and handoff
- **CLAUDE.md** covers:
  - Read `docs/HANDOFF.md` and `docs/PROGRESS.md` first.
  - Model routing: Opus plans; Sonnet implements; Haiku does docs and small tasks.
  - Tests before code.
  - The git flow.
  - The layer rules.
  - Advisory-only principles.
  - No secrets in a public repo: keys are generated at runtime and gitignored.
  - At the end of every session, dispatch a Haiku subagent to update `PROGRESS.md` and `HANDOFF.md` (done, next, open questions, how to run).
- `docs/DECISIONS.md` holds the ADRs, for example ADR-001 (same-table history), ADR-002 (no Verhoeff by default), ADR-003 (Ed25519).

## Verification (end to end)
- `scripts/test.ps1` runs pytest (rules, permissions, audit, ingest edge cases, verification) and Vitest.
- `python -m app.seed --reset`, then `uvicorn app.main:app`, then `npm run dev`. Walk demo cases 1–10 manually, then run the Playwright script that does the same.
- `POST /audit/verify` returns ok. Tamper with a row, and verify reports that row's id.
- Change one character of a QR token and the public `/verify` page shows "tampered".
- `docker compose up` on a clean checkout serves both apps.
