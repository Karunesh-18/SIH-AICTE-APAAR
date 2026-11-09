# Architecture

Last updated: 2026-11-09.

Status: this is the planned design. Only the scaffold exists in code today (see `PROGRESS.md`). Anything not marked as built is proposed.

## Summary

The system has two apps:

- **Backend:** one FastAPI app. It is a modular monolith. One process serves the API and runs the background work.
- **Frontend:** one Next.js app (App Router, TypeScript).

Data is stored in SQLite for local runs. The schema is kept Postgres-compatible, so a later move is possible. All of it runs on one laptop for the demo.

## Layers

The plan gives this chain:

```
api -> services -> domain (pure) -> adapters
```

Read it this way:

- The API layer calls services.
- Services call the domain functions and the adapters.
- The domain has no framework imports. It does not call services or adapters.
- Adapters sit behind narrow interfaces (Protocols). Services depend on the interface, so a stub can replace a real system.

| Layer | Folder | What it holds | Rule |
|---|---|---|---|
| API | routes in `backend/app/` (folder name not fixed yet) | HTTP routes, request and response models, auth checks | Pydantic v2 with `extra="forbid"`. Unknown fields are rejected. Role and object checks happen here and again in services. |
| Services | `backend/app/services/` | Use cases: ingest, validation, records, review, windows, consent, verification, audit, notify | One transaction per use case through `uow(db)`. The record, its history and its audit entry are written together. |
| Domain | `backend/app/domain/` | Pure functions: APAAR ID rules, the rules R01 to R12, intake maths, similarity, reminder ladder, consent decision, masking, record status | No framework imports. These are the main test targets. |
| Adapters | `backend/app/adapters/` | Registry, email, SMS | Each one has a stub now and a real version later. |
| Core | `backend/app/core/` | Settings, clock, password hashing and JWTs, signing keys | Shared by all layers. |

## Modules

### Core (`backend/app/core/`)

| File | Purpose |
|---|---|
| `config.py` | Settings through pydantic-settings. |
| `clock.py` | `now()`. The time comes from the real clock plus an offset stored in `system_config`. The offset lets the demo move time forward. |
| `security.py` | bcrypt password hashes. HS256 access and refresh tokens. |
| `signing.py` | Ed25519 key for verification tokens. Generated on first run into `keys/`, or read from the environment. `keys/` is gitignored. |

### Domain (`backend/app/domain/`)

| File | Purpose |
|---|---|
| `apaar.py` | `normalize(id)`, `check_format(id, checksum)`, `mask(id)` (gives `XXXX XXXX 1234`), `verhoeff_ok`. |
| `rules/` | One function per rule, R01 to R12. Each takes input and parameters and returns a list of flag drafts. Each flag draft holds the rule, a reason key, the evidence and the record references. |
| `intake.py` | Allowed enrolment is intake plus supernumerary seats. Excess rows are the last N by admission date. The evidence says this is only an ordering. |
| `similarity.py` | TF-IDF over character n-grams (2 to 4) with cosine similarity. Used by R08 and by the loose name match in R03. |
| `ladder.py` | Which reminder steps fire. Only the latest due step fires. Earlier due steps are logged as SKIPPED and never sent late in a burst. |
| `consent.py` | `decide(request, consents, policy, now)` returns `Allow(fields)` or `Refuse(reason)`. |
| `masking.py` | `serialize_record(record, viewer)`. Masking happens on the server for each role and scope. |
| `status.py` | The record state machine: submitted, valid, flagged, pending_apaar, withdrawn. |

### Services (`backend/app/services/`)

| File | Purpose |
|---|---|
| `ingest.py` | Detects the file format and reads CSV, XLSX, XLS or JSON rows. Normalises them. |
| `validation.py` | Loads the active rule versions, runs the domain rules, writes flags, updates record status, queues notifications. |
| `records.py` | Versions (current row plus superseded rows), withdraw, audited view, re-run checks when an APAAR ID is added. |
| `review.py` | Flag state changes. Each change needs a note. Also the R08 link and dismiss actions. |
| `rules_admin.py` | Rule versions, diff and revert. |
| `windows.py` | Submission windows and the reminder cycle. Run by APScheduler. Idempotent through `UNIQUE(window, institution, step)`. |
| `anomaly.py` | R09 to R12 on a schedule. |
| `dashboards.py`, `reports.py` | Both read the same queries, so the numbers match. Reports export CSV. Each export is audited. |
| `consent.py`, `verifiers.py`, `verification.py` | Consent-checked verification, verifier approval, signed results, institution notices. |
| `audit.py` | `append()`, `verify()` and the demo-only tamper endpoint. |
| `notify.py` | Writes to the transactional outbox. A dispatcher sends after commit. |
| `apikeys.py` | Per-institution API keys. |

### Adapters (`backend/app/adapters/`)

| Port | Stub now | Real target later | Notes |
|---|---|---|---|
| `RegistryAdapter` (Protocol) | `MockRegistry`, reads the seeded `registry_entry` table | The APAAR registry | A real lookup needs authorisation from the issuing authority. Not available. |
| Email | `ConsoleEmail` (writes to the console) | SMTP | The idea doc names SMTP. The plan starts with the console stub. |
| SMS | `StubSms` (writes a row to the database) | An SMS provider | No provider is chosen. |

Nothing outside the adapters talks to a real external system.

## Background work

| Work | Runs in | Notes |
|---|---|---|
| Upload checks | FastAPI `BackgroundTasks` | The result page polls. Marked in code as in-process, to move to a queue at scale. If the process stops during a check, the plan does not say how the check is retried. |
| Reminders and scheduled rules (R09 to R12) | APScheduler, in process | Safe to run twice. `window_alert_log` has `UNIQUE(window, institution, step)`. |
| Notifications | Outbox table, then a dispatcher | A message is sent only if the change that caused it was saved. |

## Clock

All time checks should go through `clock.now()`. That includes reminder steps, verification expiry and consent expiry. This is what lets the demo move time forward. The plan has the clock with an offset stored in `system_config`. Using it everywhere is our rule for the code.

## Flow of an upload

This is the planned path for a file upload (`POST /uploads`). The JSON batch endpoint (`POST /institutions/{id}/students`) runs the same checks.

1. **Send.** The institution uploads a file in the browser, or its ERP sends JSON with an API key or a JWT. The API checks the role and the institution scope. Every API key use is audited.
2. **Detect format.** The parser is chosen from the file: CSV (UTF-8, BOM allowed), XLSX (openpyxl), XLS (xlrd) or JSON.
3. **Check the file as a whole.** If the file cannot be read, or required columns are missing, the whole file is rejected. The response names the problem. No student records are written. This is the one case where a file is refused. It is not a rule about data.
4. **Normalise rows.** Spaces and hyphens are removed from APAAR IDs. Text is trimmed. Dates are read day first. Devanagari text is kept as UTF-8.
5. **Compare the file hash.** The file hash is stored with the upload. If the same file was uploaded before, the rows create new versions. They do not create copies.
6. **Save the receipt.** The upload row and the student records are written in one transaction, with their audit entries. The receipt (upload ID) is returned straight away. New records start as `submitted`.
7. **Run checks in the background.** The validation service loads the active rule version for each rule. It runs R01 to R07 on the upload. R05 and R08 also compare with other institutions' current records. Each failed check creates a `validation_flag` row. The flag stores the rule version it was raised under, the reason, the evidence and the record references.
8. **Set record status.** Records with no problems become `valid`. Records with a flag become `flagged`. Records with no APAAR ID become `pending_apaar`. Good rows are accepted. Flagged rows stay in the upload and stay visible.
9. **Commit and notify.** The checks and status changes are committed. The notification outbox is then sent. Email goes to the console stub. SMS is written to the database.
10. **Show the result.** The result page polls `GET /uploads/{id}`. It shows the received, accepted and flagged counts, and each flag with its rule code and reason.

## Record versions

A correction or a new upload creates a new current row for the record. The old row is kept with `is_current` false, `superseded_at` set and `superseded_by` set. Nothing is deleted. A withdrawn record gets status `withdrawn` and a reason. It stays in the history. See `DATA-MODEL.md` for the unique index that makes this work.

## Audit

Every write, every single-record view, every export, every verification and every refusal writes an audit entry in the same transaction as the change it records. List and dashboard reads are not audited.

Each entry stores the SHA-256 of the previous entry's hash plus the entry's own canonical JSON. `verify()` walks the chain and returns the first entry that does not match. A database `UNIQUE` on `prev_hash` stops two writers from extending the same entry.

This is tamper evidence, not tamper proof. The plan has a demo-only endpoint that changes a row on purpose so that `verify()` can be shown to catch it.

## Masking

The API serializer masks student fields for each viewer. Masking is done on the server. A hidden column in the interface is not protection.

Student fields are masked by default. They are shown in full only to the record's own institution and to AICTE officers and admins. The APAAR ID is shown as `XXXX XXXX 1234`.

## Verification

1. A verifier sends an APAAR ID and a purpose. The verifier must be approved. A pending verifier is refused.
2. `consent.decide()` checks the request against the student's consent and the purpose policy.
3. If the request is refused, the refusal is audited. The plan does not say whether the institution is told about a refusal (`HANDOFF.md`, open question 7).
4. If it is allowed, the response includes only the allowed fields.
5. The result is an Ed25519 signed JWT with an expiry time and an ID (`jti`). It can be shown as a QR code.
6. A `verification_request` row is saved. The audit entry is written. The institution gets a notice with the verifier's name and purpose.

The public check (`GET /verify/{token}`) checks the signature, the expiry and revocation. A token changed by one character fails the signature check.

## Frontend

| Area | Choice |
|---|---|
| Framework | Next.js 16 (App Router), TypeScript, Tailwind v4 |
| Components | shadcn/ui (Radix). `components.json` is set to style `base-nova`, base colour `neutral`. No UI components are added yet. |
| Data | TanStack Query and TanStack Table |
| Charts | Recharts, through shadcn charts |
| Other | `qrcode.react` for QR codes. `next-themes` for light and dark themes. Lenis smooth scroll on public pages only. At most one ShaderGradient hero. |
| Public-page pieces | Copy-in pieces from Magic UI, Aceternity or React Bits, public pages only |
| Not allowed | MUI, Chakra, Mantine, HeroUI, daisyUI, Flowbite, Barba, Spline, Unicorn |

Planned `lib/` files:

| File | Purpose | State |
|---|---|---|
| `lib/nav.ts` | Maps each role to its routes. Tested in `lib/__tests__/nav.test.ts`. | Built |
| `lib/api.ts` | Typed client made by `openapi-typescript`. One silent refresh on a 401. | Proposed |
| `lib/auth.tsx` | Role-aware context. | Proposed |
| `lib/i18n/{en,hi}.json` and `t()` | English and Hindi strings from day one. | Proposed |

Every screen must have empty, loading and error states.

Next.js here has breaking changes. Read the guides in `frontend/node_modules/next/dist/docs/` before using a Next API (see `frontend/AGENTS.md`).

## How it runs

| Mode | Parts | Status |
|---|---|---|
| Local | `uvicorn app.main:app` on port 8000. `next dev` on port 3000. SQLite file (gitignored). Seed with `python -m app.seed --reset`. | Backend and frontend scaffold run. Seed not built. |
| Docker | `docker compose up` serves both apps. | Planned. Not written yet. Will be untested because Docker is not installed on the dev machine (ADR-006). |

## Known limits

- Background work runs inside the web process. A stop during a check is not retried.
- Not built: encryption at rest, a job queue, object storage, a Postgres deployment, horizontal scaling, a real registry connection.
- The verification signing key rotation is not defined.
