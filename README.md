# Waymark APAAR Hub

Our Smart India Hackathon 2026 entry for SIH 26263, the APAAR ID based student data management and verification platform for AICTE-approved institutions. Team Phoenix Crew, Team ID 199751.

## Files
- `Waymark APAAR SIH 2026 - 6pg.pdf` and `.pptx`: the 6-page deck.
- `docs/design.md`: what is built and what is only proposed, the validation rules, and a rough data model.

## The idea
Every student record is tied to one APAAR ID. After admissions, an institution uploads its students by file or through an API. Each upload is checked for missing or badly formed IDs, repeat students, enrolment above approved intake, and fields that contradict each other. AICTE and the institutions look at the same live dashboards. An employer or regulator can verify a record only when the student has consented, and gets a signed answer back. Every change goes into an audit log chained with SHA-256. A flag never rejects anything by itself; an officer decides.

## What exists today
The base platform comes from our Waymark prototype: login with role guards, the audit chain with a verify check, an institution registry, and an obligation and alert engine with dashboards. The APAAR parts (student upload, the APAAR check, the intake and cross-institution checks, consent-based verification) are a design we have not built yet.

## Data
All names and numbers in the deck are made up. This is not an official AICTE system.
