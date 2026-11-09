# Rules catalogue (R01 to R12)

Last updated: 2026-11-09.

Status: proposed. None of the rules are built yet. R01 to R07 come first (Phase 3). R09 to R12 come in Phase 5. R08 comes in Phase 7.

## How the rules work

- Each rule has a code, R01 to R12. A flag, a report and a log line all use the same code.
- Each rule is a pure function in `backend/app/domain/rules/`. It takes the input and the rule's parameters. It returns flag drafts.
- Parameters live in the `rule_version` table as JSON. Changing a rule creates a new version. A flag keeps the version it was raised under.
- Each rule has a `message_en` and a `message_hi`.
- Rules only flag. They never reject, correct or penalise anything. An officer decides.

### Scope

| Scope | Meaning | Rules |
|---|---|---|
| `upload` | Checks one upload when it arrives | R01, R02, R03, R04, R06, R07 |
| `cross` | Compares this upload with other institutions' current records. Runs on arrival and again when the data changes. | R05, R08 |
| `scheduled` | Looks at patterns over time. Runs on a timer. | R09, R10, R11, R12 |

### Summary

| Code | Name | Catches | Scope | Phase |
|---|---|---|---|---|
| R01 | ID missing | A record with no APAAR ID | upload | 3 |
| R02 | ID format | An ID that is not 12 digits after cleaning | upload | 3 |
| R03 | Registry lookup | An ID the registry does not know, or details that do not match | upload | 3 |
| R04 | Duplicate in file | The same ID twice in one upload | upload | 3 |
| R05 | Same ID at two institutions | The same ID active at two institutions in one cycle | cross | 3 |
| R06 | Intake cap | Enrolment above intake plus supernumerary seats | upload | 3 |
| R07 | Consistency | Contradicting fields, or missing mandatory fields | upload | 3 |
| R08 | Near duplicate | Similar name and same date of birth, with different or missing IDs | cross | 7 |
| R09 | Late or missing submission | No submission by the end of the window | scheduled | 5 |
| R10 | Enrolment jump | Enrolment rises by more than a set percentage on the last cycle | scheduled | 5 |
| R11 | Pending APAAR share | Share of records pending APAAR is above a set percentage | scheduled | 5 |
| R12 | Late bulk submission | A large share arrives in the last hours of the window, with an unusual category mix | scheduled | 5 |

The thresholds in R10, R11 and R12 are placeholders. AICTE is expected to set them. The team has no data to justify a number.

---

## R01: ID missing

- **Catches:** A row with no APAAR ID.
- **Scope:** upload.
- **Params:** none in the plan.
- **Evidence:** row number, programme, cycle year.
- **Outcome:** The flag asks the institution to add the ID. The record is held as `pending_apaar`. It is counted on its own and is not rejected. When an ID is added, the checks run again.
- **Example:** "Row 23 has no APAAR ID. The record is held as pending APAAR until an ID is added. Nothing else in the file is affected."
- **Note:** The idea doc says a missing ID is "returned to the institution to fix" and also "held as pending APAAR, not rejected." This file follows the second reading. The team should confirm it. See `HANDOFF.md`.

## R02: ID format

- **Catches:** An ID that is not 12 digits after spaces and hyphens are removed.
- **Scope:** upload.
- **Params:**
  - `checksum`: `none` or `verhoeff`. Default `none`. See ADR-002.
- **Evidence:** the raw value, its length after cleaning, row number.
- **Example:** "Row 58 has an APAAR ID with 11 digits. An APAAR ID has 12. Please correct it and upload the file again."
- **Note:** With `checksum: none` the rule checks length and digits only. The plan does not claim a check digit.

## R03: Registry lookup

- **Catches:** An APAAR ID the registry does not know, or a name or date of birth that does not match the registry.
- **Scope:** upload.
- **Params:**
  - `registry_enabled`: on or off. The rule runs only when a registry adapter is connected. In the demo this is `MockRegistry`.
  - Name match: a loose comparison that treats a close match as a match. The threshold is not set in the plan.
  - Date of birth comparison rule: not set in the plan.
- **Evidence:** the file value, the registry value, the similarity score for the name, row number.
- **Outcome:** The record is held for review. A close name match is not flagged.
- **Example:** "Row 17: the registry has no entry for this APAAR ID. The record is held for review. An officer will check it."
- **Note:** The loose name match uses the same `similarity.py` as R08.

## R04: Duplicate in file

- **Catches:** The same APAAR ID on two or more rows of one upload.
- **Scope:** upload.
- **Params:** none.
- **Evidence:** the ID, the row numbers, and the admission dates on those rows.
- **Outcome:** The institution is asked which row is correct.
- **Example:** "APAAR ID 9999 0000 0041 appears on rows 41 and 97 of this file, with different admission dates. Please tell us which row is correct and upload a corrected file."

## R05: Same ID at two institutions

- **Catches:** The same APAAR ID active at two institutions in the same cycle.
- **Scope:** cross. Runs on arrival and when data changes.
- **Params:**
  - `same_cycle_only`: true. Matches only the same cycle year.
  - `lookback_cycles`: 0. A check across earlier cycles is off by default. Proposed parameter.
  - Withdrawn records do not count.
- **Evidence:** both institutions, both programmes, both admission dates.
- **Outcome:** Both institutions get an alert. An officer gets a flag. The platform does not decide which record is right.
- **Example:** "This APAAR ID is listed at two institutions in this cycle: Kaveri Valley College (MBA, admitted 12 July) and Northfield Institute (MBA, admitted 3 October). If the student transferred, mark one record withdrawn."
- **Open question:** Does the alert show the other institution's name to the first institution? See `ROLES.md`.

## R06: Intake cap

- **Catches:** Enrolment in a programme above allowed enrolment.
- **Scope:** upload.
- **Params:** none beyond the programme's own values. `approved_intake` and `supernumerary_seats` are set by AICTE and are read-only for institutions.
- **Rule:** allowed = approved intake + supernumerary seats. If seats are not set, allowed = intake alone.
- **Evidence:** approved intake, supernumerary seats, allowed, actual count, and the excess rows. Excess rows are the last N by admission date. The evidence notes that this is only an ordering.
- **Outcome:** The excess rows go to an officer. Nothing is rejected.
- **Example:** "Allowed enrolment for this programme is 126 (intake 120 plus 6 supernumerary seats). The file lists 132 students, 6 more than allowed. An officer will review the 6 records listed below."

## R07: Consistency

- **Catches:** Fields that contradict each other, and mandatory fields that are missing.
- **Scope:** upload.
- **Params:** a list of checks, stored with the rule. Examples from the idea doc: an admission date in the future, and a year of study that does not exist for the programme. Which fields are mandatory per institution type is not set (open question).
- **Evidence:** the field names, their values, the row number.
- **Example:** "Row 88 has an admission date in a later year than the cycle year. Please check it and upload again."
- **Note:** The list of checks is stored in the database, so AICTE can add a check without a code change.

## R08: Near duplicate

- **Catches:** Two records with similar names, the same date of birth, and different or missing APAAR IDs. They may be the same person.
- **Scope:** cross.
- **Params:**
  - Method: TF-IDF over character n-grams (2 to 4), cosine similarity.
  - Similarity threshold: not set in the plan.
  - Date of birth must match.
- **Evidence:** both records, the similarity score.
- **Outcome:** A suggestion only. An officer links the records or dismisses the suggestion. The platform never merges or rejects.
- **Example:** "These two records have similar names (similarity 0.91) and the same date of birth but different APAAR IDs. They may be the same person. This is a suggestion only."

## R09: Late or missing submission

- **Catches:** An institution has not submitted by the end of its submission window.
- **Scope:** scheduled.
- **Params:**
  - The window's close date.
  - The reminder ladder. The default from the idea doc: a reminder to the institution 30, 14 and 7 days before close, and on the closing day. A message to the regional officer 3 days after close if nothing has arrived. A message to the AICTE admin 10 days after.
- **Evidence:** window, cycle year, close date, last upload date (if any).
- **Outcome:** The institution appears on the late list. The ladder steps send messages.
- **Example:** "No upload has arrived from Kaveri Valley College for the 2027 cycle. The window closed on 30 November. It is listed as late."

## R10: Enrolment jump

- **Catches:** Enrolment in a programme rises by more than a set percentage over the previous cycle.
- **Scope:** scheduled.
- **Params:**
  - `jump_percent`: placeholder. AICTE is expected to set it.
  - Needs the previous cycle's data to exist.
- **Evidence:** this cycle's count, last cycle's count, the percentage change.
- **Example:** "Malabar Pharmacy College's enrolment for B.Pharm is 48 percent above the previous cycle. The threshold is [set by AICTE]."

## R11: Pending APAAR share

- **Catches:** A large share of an institution's records has no APAAR ID.
- **Scope:** scheduled.
- **Params:**
  - `pending_percent`: placeholder. AICTE is expected to set it.
- **Evidence:** count of `pending_apaar` records, total records, the percentage.
- **Example:** "18 percent of this institution's records are pending APAAR. The threshold is [set by AICTE]."

## R12: Late bulk submission

- **Catches:** A submission that arrives in one bulk in the last hours of the window, with an unusual mix of categories.
- **Scope:** scheduled.
- **Params:**
  - `last_hours`: placeholder.
  - `category_share_percent`: placeholder.
- **Evidence:** upload time, share of rows that arrived in the last hours, the category mix.
- **Example:** "Most of this upload arrived in the last 6 hours of the window, and most of it is in one admission category. The thresholds are [set by AICTE]."
- **Note:** This is a rule, not a model. It flags a pattern. An officer judges it.
