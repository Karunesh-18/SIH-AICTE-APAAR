# Glossary

Last updated: 2026-11-09.

Terms are in alphabetical order.

| Term | Meaning |
|---|---|
| Advisory | The platform flags and routes. It never rejects, corrects or penalises data. A person decides. |
| Allowed enrolment | Approved intake plus supernumerary seats. The most a programme can enrol without an excess flag (R06). |
| Alert | A message to an institution or an officer about a rule's result. Not a decision. |
| Approved intake | The number of students AICTE approved a programme to admit. Set by AICTE. |
| Anomaly rule | A scheduled rule (R09 to R12) that looks at patterns over time. |
| APAAR ID | A 12-digit permanent academic ID. It follows a student across institutions. Linked to the Academic Bank of Credits and DigiLocker in the idea doc. The key of every student record. |
| Audit chain | The audit log. Each entry carries the SHA-256 hash of the entry before it, so a change to an old entry is visible. |
| Clear, Alert, Excess | The status shown for each institution on the AICTE dashboard. The plan does not set the exact rule for each. |
| Clock | The system time, plus an offset stored in `system_config`. The offset lets the demo move time forward. |
| Consent | A student's agreement that a named purpose may be checked, for a set list of fields, until an expiry date. Recorded through the institution. |
| Consent purpose | The reason a verifier gives for a request. One of `EMPLOYMENT`, `HIGHER_EDUCATION`, `REGULATORY`, `SCHOLARSHIP`. |
| Consent scope | The fields a consent covers. |
| Consistency rule | A rule (R07) that checks that fields agree with each other, and that mandatory fields are filled. |
| Current record | The version of a student record that is in use. Its `is_current` is true. |
| Cycle year | The admission cycle a record or programme belongs to. |
| Demo mode | A mode that enables the tamper endpoint. Off outside the demo. |
| Evidence | The numbers and rows a flag used. Stored with the flag so the officer can check them. |
| Excess | Enrolment above allowed enrolment. |
| File hash | A SHA-256 of an uploaded file. Shows that the same file was sent twice. |
| FN | Foreign national. A student-level field. |
| Flag | A result from a rule. It names the rule, gives the reason, and shows the evidence. Moves through the states `open`, `under_review`, `resolved`, `dismissed`, `ask_institution`. |
| Flag event | One change to a flag: from-state, to-state, who, when and the note. |
| Genesis entry | The first entry of the audit chain. It has no real previous entry. The plan does not set its value. |
| Hard stop | A setting on a rule version. Its meaning is not settled. The team should decide what it does without breaking the advisory rule. See `HANDOFF.md`. |
| Idempotent | Safe to run twice. A reminder step is stored once, so a re-run does not send it again. |
| Institution | An AICTE-approved college or a similar body. Has a region, a status and programmes. |
| Intake use | How much of a programme's allowed enrolment is used. Shown on the intake-use chart. |
| Mask | Hiding part of a value. An APAAR ID is shown as `XXXX XXXX 1234`. |
| Mock registry | A stand-in for the APAAR registry. It reads the seeded `registry_entry` table. |
| Near duplicate | Two records that may be the same person. Found by R08. A suggestion only. |
| NRI | Non-resident Indian. A student-level category. |
| OCI | Overseas citizen of India. A student-level status. |
| Outbox | A table that holds messages. A message is written in the same transaction as the change that causes it. A dispatcher sends it after commit. |
| Pending APAAR | The status of a record that has no APAAR ID yet. It is counted separately and is not rejected. |
| Programme | A course offered by an institution. Has an approved intake and supernumerary seats. |
| Purpose policy | The list of fields that a purpose may see. Editable by AICTE admins. |
| Reminder ladder | The steps of reminders for a submission window (for example 30, 14, 7 days and the closing day). |
| Revoked | A key or token that has been switched off. A revoked token is refused even if it is not expired. |
| Rule | A check with a code (R01 to R12). Pure function in the domain layer. |
| Rule version | One set of settings for a rule (enabled, parameters, messages). Each change creates a new version. |
| Scope (rule) | Where a rule runs: `upload`, `cross` or `scheduled`. |
| Scope (role or object) | What a user can see: their institution, their region, or all. |
| Signed token | A verification result. An Ed25519 signed JWT with an expiry time and an ID (`jti`). Checked with the public key. |
| Simulated clock | The demo clock. See *Clock*. |
| Submission window | The period in which an institution must upload for a cycle. Has an open date, a close date and a reminder ladder. |
| Superseded record | An older version of a record. Kept in the same table. Its `is_current` is false. |
| Supernumerary seats | Extra places that are counted in an institution's favour before an enrolment is called excess. Set by AICTE. |
| TF-IDF | Term frequency and inverse document frequency. A classical way to turn text into numbers. Used with character n-grams for name similarity in R08 and R03. |
| Tamper evidence | The audit chain shows a change. It does not stop one. |
| Upload | One file (or one API batch) from an institution. Has a receipt, counts and a status. |
| Upload receipt | The response to an upload. Gives the upload ID straight away. |
| Verification request | A verifier's request for one APAAR ID and purpose. Has an outcome (allowed or refused) and a refusal reason. |
| Verifier | An approved outside organisation that may send verification requests. New verifiers are `PENDING` until an AICTE admin approves them. |
| Window | See *Submission window*. |

Abbreviations: API (application programming interface), ERP (enterprise resource planning), JWT (JSON Web Token), OCI (overseas citizen of India), NRI (non-resident Indian), FN (foreign national), SMS (short message service), SMTP (simple mail transfer protocol).
