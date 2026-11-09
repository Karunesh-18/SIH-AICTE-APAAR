# Data model

Last updated: 2026-11-09.

Status: Phase 1 and Phase 2 tables are built, in two Alembic migrations (`backend/migrations/versions/0001_baseline_foundation.py` and `0002_student_data_flags_rules_registry.py`). Every other table is proposed. The tables below come from `docs/PLAN.md`. Anything added beyond the plan is marked. Where a "Built" section gives different columns from the plan's table, the built section wins.

## Conventions

- Primary keys are UUIDs, except `audit_log`, which uses an integer `id`.
- Tables built with `IdMixin` in `backend/app/db/base.py` carry `created_at` and `updated_at`, and a UUID key. `flag_record`, `flag_event`, `audit_log` and `system_config` do not carry them.
- `student_record` and `validation_flag` use `version_id_col` for optimistic locking.
- Schema must work on SQLite (default) and Postgres.
- APAAR IDs are normalised (spaces and hyphens removed) before they are stored or compared.
- Times come from `clock.now()`.
- Migrations use plain SQLAlchemy types. They do not import app types (ADR-011).

## Built in Phase 1

| Table | Built columns | Built checks and keys |
|---|---|---|
| `region` | id, code (unique, 4 chars), name (unique) | |
| `institution` | id, aicte_id (unique), name, type, region_id, status, contact_email | `type` in ENGINEERING, MANAGEMENT, PHARMACY, OTHER. `status` in ACTIVE, UNDER_REVIEW. |
| `programme` | id, institution_id, name, level, cycle_year, duration_years, approved_intake, supernumerary_seats | `level` in UG, PG, DIPLOMA. Intake and seats are 0 or more. Index on `institution_id`. |
| `user` | id, email (unique), password_hash, full_name, role, institution_id, language, is_active | `role` is one of the five roles. `language` is `en` or `hi`. |
| `user_region` | user_id, region_id | Composite primary key. |
| `audit_log` | id (integer), occurred_at, actor_id, actor_role, action, entity_type, entity_id, before, after, prev_hash, hash | `prev_hash` is UNIQUE (see Key constraints). Genesis `prev_hash` is 64 zeros. |
| `system_config` | key (primary key), value (JSON) | Holds the clock offset. |
| `notification` | id, user_id, channel, subject, body, related_type, related_id, status, read_at, sent_at | `channel` in IN_APP, EMAIL, SMS. `status` in QUEUED, SENT, FAILED, LOGGED. Index on `user_id`. |
| `outbox` | id, kind, payload (JSON), attempts, dispatched_at | Written in the same transaction as the change. Sent after commit (ADR-009). |

Differences from the plan's table list:

- `outbox` has `dispatched_at` and `attempts`. It has no `sent_at`.
- `audit_log` and `system_config` do not carry `created_at` or `updated_at`. `audit_log` uses `occurred_at`.
- `notification` has `channel` and `status`, which the plan did not list.
- `institution` has `contact_email`, which the plan did not list.
- `user` has `email`, `password_hash`, `full_name`, `is_active` and `language`. The plan's `user` row said only "login fields".
- `audit_log` rows are written only by `services/audit.py`. Nothing else writes to the table.

## Built in Phase 2

| Table | Built columns | Built checks and keys |
|---|---|---|
| `upload` | institution_id, cycle_year, source, format, file_hash, row_count, accepted_count, flagged_count, status, uploaded_by, error | `source` in FILE, API. `format` in csv, xlsx, xls, json, api. `status` in RECEIVED, PROCESSING, DONE, REJECTED. Indexes on `institution_id` and `file_hash`. The same file sent twice is two uploads with the same hash. |
| `student_record` | apaar_id (32 characters, nullable, indexed), name, dob, programme_id, cycle_year, year_of_study, admission_date, admission_category, nri, oci, fn, status, version, is_current, superseded_at, superseded_by, withdrawn_reason, continues_record_id, consent_ref, consent_source, upload_id, row_number, lock_version | `status` in submitted, valid, flagged, pending_apaar, withdrawn (`ck_record_status`). `year_of_study` and `version` at least 1. `admission_category` not empty. Partial unique index `uq_record_current` on (apaar_id, programme_id, cycle_year) where `is_current` and `apaar_id` is not null. Optimistic locking through `lock_version`. |
| `validation_flag` | rule_code, rule_version_id, institution_id, upload_id, reason_key, reason, evidence (JSON), state, assignee_id, lock_version | `state` in open, under_review, resolved, dismissed, ask_institution (default open). Indexes on `rule_code`, `institution_id` and `state`. Optimistic locking through `lock_version`. |
| `flag_record` | flag_id, record_id | Composite key (flag_id, record_id). Index on `record_id`. |
| `flag_event` | id, flag_id, from_state, to_state, actor_id, note, at | The history of a flag. Index on `flag_id`. |
| `rule` | code (4 characters, unique), scope, title | `scope` in upload, cross, scheduled. |
| `rule_version` | rule_code, version_no, enabled, params (JSON), hard_stop, message_en, message_hi, created_by, note, is_active | Unique (rule_code, version_no). Partial unique index `uq_rule_one_active` on rule_code where `is_active`, so one active version per rule. |
| `registry_entry` | apaar_id (12 characters, unique), name, dob | The mock registry that R03 reads. It is not the national registry. |

Differences from the plan's table list:

- `student_record.apaar_id` holds the normalised text as submitted, even when malformed, so it is 32 characters wide. The checks flag a bad ID; they never rewrite it.
- The values of `upload.status` are set in code. The plan does not set them.
- `flag_event` and `flag_record` have no `created_at` or `updated_at`.
- Seeded APAAR IDs start with `9999` (ADR-014).

## Tables

### Reference data

| Table | Main columns | Notes |
|---|---|---|
| `region` | name | Officers are scoped to regions. |
| `institution` | aicte_id, name, type, region_id, status | `aicte_id` is the AICTE permanent ID. |
| `programme` | institution_id, name, level, cycle_year, duration_years, approved_intake, supernumerary_seats | Read-only for institutions. Set by AICTE. |

### People and access

| Table | Main columns | Notes |
|---|---|---|
| `user` | role, institution_id, plus login fields | Role is one of the five roles in `ROLES.md`. A verifier user links to a `verifier` row. The link column name is not set in the plan. |
| `user_region` | user_id, region_id | Many to many. Scopes an AICTE officer to regions. |
| `api_key` | institution_id, hash, prefix, scopes, revoked_at | Only the hash is stored. Scope is `records:submit`. Every use is audited. |

### Uploads and records

| Table | Main columns | Notes |
|---|---|---|
| `upload` | institution_id, cycle_year, source, format, file_hash, row_count, status, accepted_count, flagged_count, uploaded_by | `status` values are not set in the plan. |
| `student_record` | apaar_id (nullable), name, dob, programme_id, cycle_year, year_of_study, admission_date, admission_category, nri, oci, fn, status, version, is_current, superseded_at, superseded_by, withdrawn_reason, continues_record_id, consent_ref, upload_id | History is kept as superseded rows in this table (ADR-001). |

Fields `name` and `dob` were added by the plan. They are masked by default.

`continues_record_id` lets a returning student's record point to an earlier record. The plan keeps this for later cross-cycle work. The cross-cycle check is off by default.

### Checks and flags

| Table | Main columns | Notes |
|---|---|---|
| `rule` | code, scope (`upload`, `cross` or `scheduled`) | One row per rule, R01 to R12. |
| `rule_version` | rule_code, version_no, enabled, params (JSON), hard_stop, message_en, message_hi, created_by, note, is_active | Every change creates a new row. A revert copies an old row into a new version. |
| `validation_flag` | rule_code, rule_version_id, upload_id, reason_key, reason (rendered), evidence (JSON), state, assignee | `rule_version_id` is a snapshot. A flag keeps the rule version it was raised under. |
| `flag_record` | flag_id, record_id | Many to many. A flag can point to several records. |
| `flag_event` | flag_id, from_state, to_state, actor, note, at | The history of a flag. Every state change needs a note. |

Flag states: `open`, `under_review`, `resolved`, `dismissed`, `ask_institution`.

### Consent and verification

| Table | Main columns | Notes |
|---|---|---|
| `registry_entry` | apaar_id, name, dob | The mock registry data. |
| `consent` | apaar_id, purposes[], fields[], source, given_at, expires_at, withdrawn_at, recorded_by | Recorded through the institution. |
| `purpose_policy` | purpose, allowed_fields[], version | One row per purpose. Purposes are `EMPLOYMENT`, `HIGHER_EDUCATION`, `REGULATORY`, `SCHOLARSHIP`. Editable by admins. |
| `verifier` | org, type, contact, requested_purposes, status, decided_by, decision_note | New rows start as `PENDING`. |
| `verification_request` | verifier_id, apaar_id, purpose, fields_requested, consent_id, outcome, refusal_reason, token_jti, expires_at, revoked_at | Refusals are stored too. |

### Time, reminders and messages

| Table | Main columns | Notes |
|---|---|---|
| `submission_window` | cycle_year, institution_type (null = all), opens_at, closes_at, ladder (JSON) | The ladder holds the reminder steps `{step, offset_hours, audience}`. Built (Phase 5, migration 0004). |
| `window_alert_log` | window_id, institution_id, step, status (SENT or SKIPPED) | `UNIQUE(window, institution, step)`. Built. |
| `saved_report` | user_id, name, report_key, filters (JSON) | A report definition, private to its user. Built. |
| `notification` | recipient, kind, body, read_at | Shown on the bell. |
| `outbox` | payload, created_at, sent_at | Written in the same transaction as the change. A dispatcher sends after commit. |

### Control

| Table | Main columns | Notes |
|---|---|---|
| `audit_log` | id (integer), actor, action, target, before, after, at, prev_hash, hash | Hash-chained. |
| `system_config` | key, value | Holds the clock offset and similar settings. |
| `saved_report` | name, definition | Report definitions that can be re-run. |

## Key constraints

| Constraint | Where | Why | Source |
|---|---|---|---|
| Partial unique index on `(apaar_id, programme_id, cycle_year)` where `is_current` and `apaar_id` is not null | `student_record` | One current record per student, per programme, per cycle. Superseded rows may repeat. Works on SQLite and Postgres. | Plan. Built in Phase 2 (`uq_record_current`). |
| `UNIQUE(window, institution, step)` | `window_alert_log` | A reminder step fires once. A re-run is harmless. | Built (Phase 5) |
| `UNIQUE(prev_hash)` | `audit_log` | Two writers cannot both extend one entry. Stops the chain from forking. Built. A second concurrent writer gets an IntegrityError (HTTP 500) until a retry is added. | Plan |
| `version_id_col` (optimistic locking) | `student_record`, `validation_flag` | Two people editing one row cannot overwrite each other silently. | Plan. Built in Phase 2 (`lock_version`). |
| Stores only the hash of an API key | `api_key` | The key cannot be read back. | Plan |
| `status` is one of submitted, valid, flagged, pending_apaar, withdrawn | `student_record` | Keeps the states to a known set. A database CHECK (`ck_record_status`) enforces it. | Plan. The CHECK is built in Phase 2. |
| A flag state change needs a note | `flag_event` | The reason for each decision is kept. | Plan (service rule), not a database constraint |
| Edits to rules create a new `rule_version` row | `rule_version` | Rule history is kept. Flags can be traced to the version in force. | Plan |
| A verifier is `PENDING` until an admin approves or rejects | `verifier` | Only approved verifiers can send requests. | Plan (service rule) |
| Unknown request fields are rejected | API | Stops silent typos. | Plan (Pydantic `extra="forbid"`), not a database constraint |

Not set in the plan: foreign key delete rules, and indexes other than the ones above. The values allowed in `upload.status` are set in code (Phase 2).

## Record lifecycle

```
submitted --> valid
          --> flagged
          --> pending_apaar   (no APAAR ID yet)
          --> withdrawn       (institution withdraws it)

pending_apaar --> valid or flagged   (once an ID is added and checks are re-run)
```

The plan does not list every transition. These are not set yet:

- Whether `flagged` returns to `valid` when all its flags are resolved, and by whom.
- Whether a `withdrawn` record can be restored.

Both should be decided before Phase 4.

## Versions in practice

- Correction or re-upload: the old current row becomes superseded (`is_current` false, `superseded_at` set, `superseded_by` set). A new current row is written.
- Withdraw: status becomes `withdrawn`, the reason is saved, and the row stays.
- Nothing is deleted.
- The history view shows every version of one record.


## Phase 3 additions (migration 0003)

`api_key` (built): institution_id, name, prefix (first 8 characters of the token), key_hash (sha256, unique), scope (`records:submit`), created_by, revoked_at, last_used_at. The token itself is never stored.

Ingestion notes: a row whose name, date of birth or admission date cannot be read is stored with an empty name, `0001-01-01`, or category `UNSPECIFIED` (those columns are NOT NULL) and flagged by R07. Re-uploading creates new versions: the earlier current row gets `is_current` false, `superseded_at`, `superseded_by`, and the new row has `version + 1` and `continues_record_id`. Rows with no APAAR ID are never superseded (no key to match on).

## Phase 4 (no schema change)

Phase 4 adds no tables or columns. It uses `validation_flag.lock_version` and `assignee_id`, `flag_event`, and on `student_record` the existing `version`, `continues_record_id`, `superseded_by`, `superseded_at` and `withdrawn_reason`. A correction adds a row with `version + 1` and the same `upload_id` and `row_number`. A withdrawn record keeps `is_current = true` (ADR-015). System closures have a `flag_event` with `actor_id` null.
