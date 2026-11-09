# Waymark APAAR Hub (SIH 26263): agent manual

AICTE student-data platform keyed by APAAR ID. Built from scratch in this repo. All data is synthetic. Not an official AICTE system.

## Start of every session
1. Read `docs/HANDOFF.md` (what was done last, what is next, open questions), then `docs/PROGRESS.md`.
2. Full plan: `docs/PLAN.md`. Product spec: `submission/idea.txt` (already submitted, never edit). Decisions: `docs/DECISIONS.md`.

## Model routing
Opus plans. Sonnet subagents implement. Haiku subagents update docs and do small, easy tasks.
**End of every session:** dispatch a Haiku subagent to update `docs/PROGRESS.md` and `docs/HANDOFF.md` (done, next, open questions, how to run).

## Rules
- **Tests before code, always.** Write the failing test, see it fail for the right reason, then implement.
- Advisory only: the platform flags and routes, never rejects, corrects or penalises. Every flag names its rule and shows its numbers.
- Layers: `api -> services -> domain (pure, no framework imports) -> adapters`. One transaction per use case; the audit entry is written in the same transaction.
- Authorisation is checked on the server by role and object scope. Hiding UI is not protection. Student fields are masked in the API serializer.
- Audit every write, single-record view, export, verification and refusal. Not list or dashboard reads.
- The repo is public: no secrets or real data. Signing keys are generated at runtime into gitignored `keys/`.
- Say what is built vs proposed. Update the built/proposed table in `README.md` and `docs/design.md` when a feature lands. Untested things (for example Docker) are labelled untested.
- Frontend: Next.js here has breaking changes. Read `frontend/node_modules/next/dist/docs/` before using a Next API.

## Git
Work on `dev`. Each feature or fix: new branch off `dev`, PR into `dev` (`gh pr create --base dev`). `dev` -> `main` by PR at milestones. Never commit to `main` directly.

## Run
- Backend: `cd backend; .\.venv\Scripts\python -m uvicorn app.main:app --reload` (Python 3.11 venv, pip).
- Frontend: `cd frontend; npm run dev`.
- Tests: `scripts\test.ps1`.
- Android/Gradle is unrelated to this repo.
