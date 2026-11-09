# Waymark APAAR Hub

Our Smart India Hackathon 2026 entry for SIH 26263, the APAAR ID based student data management and verification platform for AICTE-approved institutions. Team Phoenix Crew, Team ID 199751.

## Files
- `Waymark APAAR SIH 2026 - 6pg.pdf` and `.pptx`: the 6-page deck.
- `docs/design.md`: the earlier design note (built vs proposed, validation rules, rough data model).
- `submission/`: the submitted title, abstract and idea text. Not edited.

## The idea
Every student record is tied to one APAAR ID. After admissions, an institution uploads its students by file or through an API. Each upload is checked for missing or badly formed IDs, repeat students, enrolment above approved intake, and fields that contradict each other. AICTE and the institutions look at the same live dashboards. An employer or regulator can verify a record only when the student has consented, and gets a signed answer back. Every change goes into an audit log chained with SHA-256. A flag never rejects anything by itself; an officer decides.

## Status

The code in this repo is being built from scratch. Earlier prototypes were not copied (see `docs/DECISIONS.md`, ADR-004). Right now only the scaffold exists. Everything else is proposed.

| Part | Status |
|---|---|
| FastAPI backend with a `/health` endpoint and a test | Built (scaffold only) |
| Next.js frontend with the role-to-route nav map and its test | Built (scaffold only; the home page is still the starter page) |
| Test script `scripts/test.ps1` | Written. Not yet confirmed green. |
| Login, roles, object-level scoping | Proposed |
| Audit chain with verify and tamper check | Proposed |
| Institution and region registry | Proposed |
| Student upload (CSV, XLSX, XLS, JSON) and the API batch endpoint | Proposed |
| Rules R01 to R07 on upload | Proposed |
| Registry lookup against a mock registry (R03) | Proposed |
| Review queue, flag notes, record versions and withdrawal | Proposed |
| Submission windows, reminders, the simulated clock | Proposed |
| Dashboards, reports, scheduled rules R09 to R12 | Proposed |
| Consent, verifier approval, Ed25519 signed results, QR check | Proposed |
| Near-duplicate names with TF-IDF (R08) | Proposed |
| English and Hindi text | Proposed |
| `docker compose up` | Proposed. Written later, **untested** (Docker is not installed on the dev machine). |

Phase 0 of 7 is in progress. See `docs/PROGRESS.md`.

## Docs
- `docs/PLAN.md`: the approved build plan.
- `docs/ARCHITECTURE.md`: layers, modules, adapters, and the flow of an upload.
- `docs/DATA-MODEL.md`: tables and key constraints.
- `docs/API.md`: endpoint outline. All proposed.
- `docs/RULES.md`: the rules R01 to R12.
- `docs/ROLES.md`: the five roles and object-level scope.
- `docs/GLOSSARY.md`: terms used across the project.
- `docs/DECISIONS.md`: architecture decision records.
- `docs/PROGRESS.md`: phase status.
- `docs/HANDOFF.md`: how to run the project, next steps, open questions.

## Data
All names and numbers in the deck are made up. This is not an official AICTE system.
