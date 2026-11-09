# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack
Next.js 16 (App Router), TypeScript, Tailwind v4, shadcn/ui on Radix, TanStack Query and Table, Recharts. Backend is FastAPI in `../backend`.

## Users
Primary: AICTE officers who work a review queue of flags across many institutions, region-scoped, all day. Secondary: institution admissions staff who upload student files and fix the rows that were flagged; AICTE admins who set rules; approved verifiers (employers, institutions, regulators) who send consent-checked verification requests. Hackathon judges will also walk the demo. Students are not users in v1.

## Product Purpose
Waymark APAAR Hub (SIH 26263, Team Phoenix Crew) holds one verified record per student, keyed by APAAR ID, for AICTE-approved institutions. Institutions upload by file or API, each upload is checked by plain rules, flags go to a human review queue, and verifiers get signed, consent-limited answers. Success: AICTE sees excess and duplicate enrolment while a cycle is still open, and institutions get exact rows and reasons instead of a vague rejection.

## Positioning
Advisory, explainable and tamper-evident: every flag names its rule and shows its numbers, nothing is rejected or corrected automatically, every action is in a SHA-256 hash-chained audit log, and verification results are Ed25519-signed and publicly checkable by QR.

## Operating Context
Officers work from desk machines with wide screens and long tables. Institution staff upload CSV, XLSX, XLS or JSON files exported from their own systems. Verification results are shown or printed with a QR code that opens a public check page. UI is English and Hindi from day one; light and dark themes.

## Capabilities and Constraints
Five roles: AICTE_ADMIN, AICTE_OFFICER, INSTITUTION_ADMIN, INSTITUTION_STAFF, VERIFIER. Rules R01-R12 are editable with version history and revert. Student fields (name, DOB, APAAR ID) are masked server-side except for the record's own institution and AICTE officers/admins. Flag states: open, under review, resolved, dismissed. Institution status: Clear, Alert, Excess. Record status: submitted, valid, flagged, pending APAAR, withdrawn. All data is synthetic and the platform makes no claim of integration with the real APAAR registry or AICTE portal.

## Brand Commitments
Own identity only: "Waymark APAAR Hub", Team Phoenix Crew. No AICTE or Government of India logo or emblem. A visible notice that this is a prototype on synthetic data and not an official AICTE system. AICTE is named as text only where it describes the regulator.

## Evidence on Hand
No real institutions, students or testimonials exist and none may be invented as real. Sample data is fictional (Kaveri Valley College, Northfield Institute, Malabar Pharmacy College). Source documents: `../submission/idea.txt`, `../docs/PLAN.md`, deck PDF in repo root.

## Product Principles
1. A human decides; the interface recommends, flags and routes.
2. Show the reason and the numbers next to every flag.
3. Optimise for the officer's triage loop first; other roles get calmer, guided views.
4. Say plainly what is built versus proposed, and what is synthetic.
5. Authorisation is real on the server; the UI never relies on hiding things.

## Accessibility & Inclusion
Target WCAG 2.1 AA. Status must never rely on colour alone. Full keyboard operation for tables and the review queue. Hindi (Devanagari) must render and fit as well as English.
