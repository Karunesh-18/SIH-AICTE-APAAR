# Waymark APAAR Hub

Smart India Hackathon 2026, **SIH 26263**: Development of an APAAR ID-Based Student Data Management and Verification Platform for AICTE-Approved Institutions.
Team Phoenix Crew (Team ID 199751).

## What is here
- `Waymark APAAR SIH 2026 - 6pg.pdf` and `.pptx`: the 6-page submission deck.
- `docs/design.md`: scope, what is built vs proposed, validation rules and the data model sketch.

## Idea in one paragraph
Every student record is keyed by APAAR ID. Institutions upload student data after admissions (file or API). Rule-based checks flag missing or malformed IDs, duplicates, admissions above approved intake and contradicting fields. AICTE and institutions watch the same live dashboards. Authorised parties verify a record only with the student's consent and get a signed result. Every change is written to a hash-chained audit log. Flags are suggestions; officers decide.

## Honest status
The platform backbone comes from the Waymark prototype (login with role guards, SHA-256 audit chain with a verify check, institution registry, obligation and alert engine, dashboards). The APAAR-specific parts (student upload, APAAR validation adapter, intake and cross-institution checks, consent-based verification) are a proposed design, not built yet.

## Data
All figures and names in the deck are synthetic. This is not an official AICTE system.
