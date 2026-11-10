# Waymark APAAR Hub

Our Smart India Hackathon 2026 entry for SIH 26263: an APAAR ID based student data management and verification platform for AICTE-approved institutions. Team Phoenix Crew, Team ID 199751.

## The idea

Every student record is tied to one APAAR ID. After admissions, an institution uploads its students by file or through an API. Each upload is checked for missing or badly formed IDs, repeat students, enrolment above approved intake, near-duplicate names and fields that contradict each other. AICTE and the institutions look at the same dashboards. An employer or regulator can verify a record only when the student has consented, and gets a signed answer back. Every write, view, export, verification and refusal goes into an audit log chained with SHA-256. A flag never rejects anything by itself; an officer decides.

## Status

All eight phases of the build plan are built, and later work is merged to `dev`. The platform runs on SQLite with synthetic data. A browser pass was done and its findings are fixed, but not every screen is recorded as checked. The Docker path is untested.

| Part | Status |
|---|---|
| FastAPI backend: JWT login and refresh (refresh tokens rotate with reuse detection, ADR-026), five roles, object-level scope, permission matrix over every route | Built. Tested. |
| Audit chain with verify and a tamper demo | Built. Tested. |
| Institutions, users, staff, regions and API keys (per institution, scope `records:submit`) | Built. Tested. |
| Student upload (CSV, XLSX, XLS, JSON), templates, and the REST batch endpoint | Built. Tested. |
| Rules R01 to R07 on upload, with versioned parameters, edit, diff and revert | Built. Tested. |
| R03 registry lookup | Built against a mock registry. A real registry needs authorisation (not built). |
| R05 same ID at two institutions, R08 near-duplicate names (TF-IDF) | Built. Tested. Thresholds are placeholders. |
| Review queue, flag actions with notes, record correction and withdrawal, history | Built. Tested. |
| Submission windows, reminder ladder, scheduled R09 to R12, late list | Built. Tested. Thresholds are placeholders. |
| Dashboards and reports (CSV export), with figures that equal each other | Built. Tested. |
| Consent ledger, purpose policies, verifier approval, Ed25519 signed results, public check API | Built. Tested. |
| Demo clock, in-app notifications, transactional outbox | Built. Email is console by default; SMTP adapter is built (see below). |
| Printable certificate record with a signed CERTIFICATE QR token | Built. Tested. QR scan not checked in a browser. |
| Beyond the submission: offline check of signed QR tokens on the public verify page (Ed25519 in the browser, cached public key, ADR-028) | Built. Unit tested. Not checked in a browser. |
| Beyond the submission: signed audit checkpoints that catch truncation of the last rows (ADR-029) | Built. Tested. UI on `/admin/audit` (PR #27). Not checked in a browser. |
| Beyond the submission: impact preview for R08, R10 and R11 rule parameters, computed and not saved (ADR-030, PR #28) | Built. Tested. Not checked in a browser. |
| Beyond the submission: rule health panel on `/admin/rules` with per-rule flag outcomes, figures only, nothing changes automatically (ADR-031, PR #29) | Built. Tested. Not checked in a browser. |
| Beyond the submission: "to clear this flag" hint on each flag, computed from its evidence, advisory wording, English and Hindi (ADR-032, PR #30) | Built. Tested. Not checked in a browser. English wording and R07 need a pass. Hindi not reviewed. |
| Frontend: role-aware screens for every role, English and Hindi, light and dark themes | Built. Types, lint, unit tests and build pass. A browser pass was done and its findings are fixed (PRs #16, #17). Charts, dialogs and layout not recorded as checked. |
| Synthetic seed, `python -m app.seed --demo` | Built. |
| Ten demo cases as one test through the HTTP API | Built. Not run in a browser. |
| Real email (SMTP) | Built behind the email interface (ADR-027, `EMAIL_BACKEND=smtp`). Tested against a fake server only. |
| SMS | Not built. Console stub. |
| Encryption at rest, a job queue, object storage | Not built. |
| `docker compose up` | Written. **Untested** (Docker is not installed on the dev machine). |

Phase status and PR numbers are in `docs/PROGRESS.md`. Known limits and open questions are in `docs/HANDOFF.md`.

## Run it locally

Windows PowerShell, from the repo root. Needs Python 3.11 and Node.js 20.9 or later.

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install fastapi "uvicorn[standard]" sqlalchemy alembic pydantic-settings pyjwt bcrypt cryptography apscheduler python-multipart openpyxl xlrd scikit-learn pytest httpx ruff xlwt
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m app.seed --demo
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. Demo logins use the password `Demo@1234`: `admin@`, `officer@`, `inst-admin@`, `staff@` and `verifier@demo.test`. Tests: `scripts\test.ps1`.

The full set of steps, the demo walk-through and the limits are in `docs/HANDOFF.md`.

## Files

- `Waymark APAAR SIH 2026 - 6pg.pdf` and `.pptx`: the 6-page deck.
- `submission/`: the submitted title, abstract and idea text. Not edited.
- `backend/`: FastAPI, SQLAlchemy, Alembic migrations, rules and tests.
- `frontend/`: Next.js App Router screens, vitest tests.
- `scripts/test.ps1`: runs both test suites.
- `docker-compose.yml`: untested.

## Docs

- `docs/PLAN.md`: the approved build plan.
- `docs/ARCHITECTURE.md`: layers, modules, adapters, and the flow of an upload.
- `docs/DATA-MODEL.md`: tables and key constraints. Built tables are marked.
- `docs/API.md`: endpoint outline. The phase sections list what is built.
- `docs/RULES.md`: the rules R01 to R12.
- `docs/ROLES.md`: the five roles and object-level scope.
- `docs/GLOSSARY.md`: terms used across the project.
- `docs/DECISIONS.md`: architecture decision records.
- `docs/design.md`: the design note, with the built and proposed table.
- `docs/PROGRESS.md`: phase status, PR numbers and the stacked PR order.
- `docs/HANDOFF.md`: how to run the project, the demo walk-through, what is unverified, known limits, open questions and next steps.

## Data

All names and numbers in the deck and in the demo seed are invented. Seeded APAAR IDs start with `9999`. This is not an official AICTE system.
