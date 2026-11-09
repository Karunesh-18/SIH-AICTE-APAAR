# Waymark APAAR Hub

Our Smart India Hackathon 2026 entry for SIH 26263, the APAAR ID based student data management and verification platform for AICTE-approved institutions. Team Phoenix Crew, Team ID 199751.

## Files
- `Waymark APAAR SIH 2026 - 6pg.pdf` and `.pptx`: the 6-page deck.
- `docs/design.md`: the earlier design note (built vs proposed, validation rules, rough data model).
- `submission/`: the submitted title, abstract and idea text. Not edited.

## The idea
Every student record is tied to one APAAR ID. After admissions, an institution uploads its students by file or through an API. Each upload is checked for missing or badly formed IDs, repeat students, enrolment above approved intake, and fields that contradict each other. AICTE and the institutions look at the same live dashboards. An employer or regulator can verify a record only when the student has consented, and gets a signed answer back. Every change goes into an audit log chained with SHA-256. A flag never rejects anything by itself; an officer decides.

## Status

The backend has its Phase 1 foundation built: login, roles, the audit chain with verify, the institutions API, the demo clock and notifications. The frontend has the login page, API client, auth context and role-aware shell. The student data tables and a synthetic seed are built. Upload, checks and the review screens are still proposed.

| Part | Status |
|---|---|
| FastAPI backend: `/health`, JWT login and refresh, role guards | Built. Tests pass. |
| Audit chain with verify and tamper demo | Built. Tests pass. |
| Institutions API (scoped by role and region) | Built. |
| Demo clock and in-app notifications, with an outbox | Built. Email is a console stub. |
| Permission-matrix test over every API route | Built. |
| Next.js frontend with the role-to-route nav map and its test | Built |
| Test script `scripts/test.ps1` | Built. Green. |
| Frontend login, API client (one refresh on 401) and role-aware shell | Built. Not yet checked in a browser. |
| Student, upload, flag, rule and registry tables (migration 0002) | Built. Tests pass. |
| Synthetic seed (`python -m app.seed`): fictional institutions, demo users, rules, mock registry | Built. Writes no flags. |
| Review queue and flag detail (`/review`), institution flags and reply, record correct and withdraw, notification bell and page | Built (frontend, Phase 4). Vitest, tsc, eslint and `next build` pass. Not checked in a browser. |
| Region admin, user admin | Proposed |
| Student upload (CSV, XLSX, XLS, JSON), templates, and the API batch endpoint with per-institution API keys (backend only) | Built. Tests pass. XLS tested with a fixture built by dev-only xlwt. |
| Rules R01 to R07 on upload, rule version admin (backend) | Built. Tests pass. |
| Frontend: upload, receipt with flags, institution home, records (masked fields), API keys, rule versions with edit, diff and revert | Built. vitest, tsc, eslint and `next build` pass. Not checked in a browser. |
| Registry lookup against a mock registry (R03) | Proposed |
| Review queue, flag notes, record versions and withdrawal | Built in the backend (Phase 4); no screens yet |
| Submission windows with reminder ladder, late list, scheduled rules R09 to R12, dashboards and reports (backend, Phase 5) | Built. Tests pass. |
| Phase 5 screens: AICTE dashboard with intake and flags-by-rule charts, institution detail, institution home status, reports (run, CSV export, save), submission windows and demo clock admin, demo clock banner | Built (frontend). Vitest, tsc, eslint and `next build` pass. Not checked in a browser. |
| Consent, verifier approval, Ed25519 signed results, QR check | Proposed |
| Near-duplicate names with TF-IDF (R08) | Proposed |
| English and Hindi text | Proposed (the API stores a language per user) |
| `docker compose up` | Proposed. Written later, **untested** (Docker is not installed on the dev machine). |

Phase 1 of 7 is in progress: the backend and the frontend shell are built, and the browser check is open. Phase 2 tables and seed are built. See `docs/PROGRESS.md`.

## Docs
- `docs/PLAN.md`: the approved build plan.
- `docs/ARCHITECTURE.md`: layers, modules, adapters, and the flow of an upload.
- `docs/DATA-MODEL.md`: tables and key constraints. Built tables are marked.
- `docs/API.md`: endpoint outline. The "Built" table lists what is in the code.
- `docs/RULES.md`: the rules R01 to R12.
- `docs/ROLES.md`: the five roles and object-level scope.
- `docs/GLOSSARY.md`: terms used across the project.
- `docs/DECISIONS.md`: architecture decision records.
- `docs/PROGRESS.md`: phase status.
- `docs/HANDOFF.md`: how to run the project, next steps, open questions.

## Data
All names and numbers in the deck are made up. This is not an official AICTE system.
