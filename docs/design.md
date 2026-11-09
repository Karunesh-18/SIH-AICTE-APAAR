# Design note: Waymark APAAR Hub (SIH 26263)

Last updated: 2026-11-10.

## Scope
Student-level data submission, validation, monitoring and consent-based verification for AICTE-approved institutions, keyed by APAAR ID.

## Built vs proposed
| Part | Status |
|---|---|
| JWT login (access and refresh, refresh tokens rotate per ADR-026), five roles, object-level institution and region scope | Built. Tested. |
| Frontend API client, auth context and role-aware shell | Built. Tokens in `localStorage` (prototype only, ADR-013). |
| Hash-chained audit log with verify and tamper demo | Built. Tested. |
| Institution registry, region model, institutions API | Built. Tested. |
| Region and user admin, staff management, API keys | Built. Tested. |
| Demo clock (advance and reset) | Built. Tested. |
| Notifications (in-app, with a transactional outbox) | Built. Email is console by default; SMTP adapter built (ADR-027). |
| Student, flag, rule and registry tables; synthetic seed (`--demo`) | Built. Tested. |
| Student upload (CSV, XLSX, XLS, JSON) and REST batch with API keys | Built. Tested. |
| Rules R01 to R07 on upload, rule versions with edit, diff and revert | Built. Tested. |
| Review queue, flag actions with notes, institution flag reply, record correction and withdrawal | Built. Tested. |
| R08 near duplicate, shared TF-IDF name similarity | Built. Tested. Threshold is a placeholder. |
| R05 same ID at two institutions | Built. Tested. |
| Submission windows, reminder ladder, scheduled rules R09 to R12, dashboards and reports | Built. Tested. Thresholds are placeholders. Charts use the palette in `frontend/app/globals.css`. |
| Consent ledger, purpose policies, verifier approval, Ed25519 signed results, public check API | Built. Tested. |
| Frontend screens for all roles, English and Hindi text, light and dark themes | Built. Types, lint, unit tests and build pass. A browser pass was done and its findings are fixed (PRs #16, #17). Charts, dialogs and layout not recorded as checked. |
| Printable certificate record with a signed CERTIFICATE QR token | Built. Tested. QR scan not checked in a browser. |
| Beyond the submission: offline check of signed QR tokens on the public verify page (Ed25519 in the browser, cached public key, ADR-028) | Built. Unit tested. Not checked in a browser. |
| Beyond the submission: signed audit checkpoints that catch truncation of the last rows (ADR-029) | Built. Tested. No UI yet. |
| Privacy masking of student fields in the API serializer | Built. Tested. |
| APAAR validation against a live registry | Proposed. Needs authorisation from the issuing authority. R03 runs on a mock. |
| Real email (SMTP) | Built behind the email interface (ADR-027). Tested against a fake server only. |
| SMS | Proposed. Console stub. |
| Encryption at rest, a job queue, object storage | Proposed. Not built. |
| `docker compose up` | Written. **Untested** (Docker is not installed on the dev machine). |

Known limits and open questions are in `HANDOFF.md`. The data model is in `DATA-MODEL.md`.

## Data per student
APAAR ID (unique key); programme, year, admission date; approved intake and actual enrolment (per programme); supernumerary seats; NRI category; OCI status; foreign national (FN) status; consent flag and source.

## Validation rules
| Rule | Catches | Result |
|---|---|---|
| ID format | Missing ID, or not 12 digits | Flag. Missing ID is held as pending APAAR. |
| Registry lookup | ID not found or details do not match | Flag. Held for review. |
| Duplicate in file | Same ID twice in one upload | Flag. The first row stays current (ADR-012). |
| Across institutions | Same ID active at two institutions | Flag. Both institutions are notified. |
| Intake cap | Enrolment above approved intake plus supernumerary seats | Flag with count |
| Near duplicate | Similar name and date of birth, different ID | Suggestion only |
| Consistency | Contradicting fields or mandatory fields missing | Flag |
| Scheduled patterns | Late submission, enrolment jump, pending share, late bulk submission | Flag. Thresholds are placeholders. |

Example: intake 120, supernumerary seats 6, allowed 126, actual 132, so 6 records go to an officer. Nothing is rejected automatically. A student without an APAAR ID yet is held as "pending APAAR", not rejected.

## Principles
Advisory only; every flag shows its rule; synthetic data only; method names stated plainly (rules, TF-IDF); no claim of AICTE portal or APAAR registry integration.

## Data model sketch
`institution` 1-n `programme` (approved_intake, supernumerary_seats) 1-n `student_record` (apaar_id, status, nri, oci, fn, admission_date, consent) ; `validation_flag` (record, rule, reason, state) ; `verification_request` (verifier, purpose, consent_ref, result, signed_token) ; `audit_log` (hash-chained).

All tables in the plan are built: the Phase 1 tables (`region`, `institution`, `programme`, `user`, `user_region`, `audit_log`, `system_config`, `notification`, `outbox`), the Phase 2 student and rule tables (`upload`, `student_record`, `validation_flag`, `flag_record`, `flag_event`, `rule`, `rule_version`, `registry_entry`), and the consent, verifier, policy and API key tables. See `DATA-MODEL.md`.
