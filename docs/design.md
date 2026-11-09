# Design note: Waymark APAAR Hub (SIH 26263)

## Scope
Student-level data submission, validation, monitoring and consent-based verification for AICTE-approved institutions, keyed by APAAR ID.

## Built vs proposed
| Part | Status |
|---|---|
| JWT login, role guards | Proposed (rebuilt in this repo from Phase 1) |
| Hash-chained audit log with verify | Proposed (rebuilt in this repo from Phase 1) |
| Institution registry, obligation and alert engine, compliance dashboard, notifications | Proposed (rebuilt in this repo from Phase 1) |
| Student upload (CSV/Excel and REST API) | Proposed |
| APAAR validation through a registry adapter | Proposed; live lookup needs authorisation from the issuing authority |
| Intake-cap, cross-institution duplicate and consistency checks | Proposed |
| TF-IDF near-duplicate name flag | Proposed (suggestion only) |
| Privacy masking of student fields in the API | Proposed |
| Consent-based verification, signed result, QR | Proposed |

Built so far in this repo: project scaffold, /health endpoint, design tokens only.

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
