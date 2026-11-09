# Design note: Waymark APAAR Hub (SIH 26263)

Last updated: 2026-11-09.

## Scope
Student-level data submission, validation, monitoring and consent-based verification for AICTE-approved institutions, keyed by APAAR ID.

## Built vs proposed
| Part | Status |
|---|---|
| JWT login (access and refresh), role guards, object-level institution scope | Built (backend). Frontend login built, not yet checked in a browser. |
| Frontend API client, auth context and role-aware shell | Built. Tokens in `localStorage` (prototype only, ADR-013). |
| Hash-chained audit log with verify and tamper demo | Built (backend) |
| Institution registry (institutions API and models), region model | Built (backend). Region and user admin proposed. |
| Obligation and alert engine, compliance dashboard | Proposed |
| Notifications (in-app, with a transactional outbox) | Built (backend). Email is a console stub. |
| Demo clock (advance and reset) | Built (backend) |
| Student, flag, rule and registry tables; synthetic seed | Built (tables and seed). No ingestion or checks yet. |
| Review queue, flag detail with per-rule evidence, institution flag reply, record correct and withdraw, notification bell (30 s poll) | Built (frontend). Not checked in a browser. |
| Student upload (CSV/XLSX/XLS/JSON and REST API with API keys), rules R01 to R07, rule versions | Built (backend and screens). Screens pass vitest, tsc, eslint and `next build` but were not checked in a browser. In-process background task, not a queue. |
| APAAR validation through a registry adapter | Proposed; live lookup needs authorisation from the issuing authority |
| Intake-cap, cross-institution duplicate and consistency checks | Proposed |
| TF-IDF near-duplicate name flag | Proposed (suggestion only) |
| Privacy masking of student fields in the API | Proposed |
| Consent-based verification, signed result, QR | Proposed |

Built so far in this repo: project scaffold, `/health`, the Phase 1 backend (auth, audit chain, institutions API, clock, notifications), the Phase 1 frontend login, API client and shell, the Phase 2 student data tables with the synthetic seed, and the design tokens. Upload, the checks and the record and flag screens are proposed.

## Data per student
APAAR ID (unique key); programme, year, admission date; approved intake and actual enrolment (per programme); supernumerary seats; NRI category; OCI status; foreign national (FN) status; consent flag and source.

## Validation rules
| Rule | Catches | Result |
|---|---|---|
| ID format | Missing ID, or not 12 digits | Fix and resubmit |
| Registry lookup | ID not found or details do not match | Held for review |
| Duplicate in file | Same ID twice in one upload | Flag |
| Across institutions | Same ID active at two institutions | Alert both |
| Intake cap | Enrolment above approved intake plus supernumerary seats | Flag with count |
| Near duplicate | Similar name and date of birth, different ID | Suggestion only |
| Consistency | Contradicting fields or mandatory fields missing | Flag |

Example: intake 120, supernumerary seats 6, allowed 126, actual 132, so 6 records go to an officer. Nothing is rejected automatically. A student without an APAAR ID yet is held as "pending APAAR", not rejected.

## Principles
Advisory only; every flag shows its rule; synthetic data only; method names stated plainly (rules, TF-IDF); no claim of AICTE portal or APAAR registry integration.

## Data model sketch
`institution` 1-n `programme` (approved_intake, supernumerary_seats) 1-n `student_record` (apaar_id, status, nri, oci, fn, admission_date, consent) ; `validation_flag` (record, rule, reason, state) ; `verification_request` (verifier, purpose, consent_ref, result, signed_token) ; `audit_log` (hash-chained).

The Phase 1 tables (`region`, `institution`, `programme`, `user`, `user_region`, `audit_log`, `system_config`, `notification`, `outbox`) and the Phase 2 tables (`upload`, `student_record`, `validation_flag`, `flag_record`, `flag_event`, `rule`, `rule_version`, `registry_entry`) are built. See `DATA-MODEL.md`.
