# Roles and scope

Last updated: 2026-11-09.

Status: built in the backend and checked by `tests/test_permission_matrix.py`. Role names are in `frontend/lib/nav.ts`.

## The five roles

| Role | Who it is for |
|---|---|
| `AICTE_ADMIN` | AICTE staff who run the platform. Sets rules, policies, users and windows. |
| `AICTE_OFFICER` | AICTE staff who review flags and reports for their assigned regions. |
| `INSTITUTION_ADMIN` | An institution's lead user. Uploads, corrects, manages API keys and staff. |
| `INSTITUTION_STAFF` | An institution user who uploads, corrects and answers flags. |
| `VERIFIER` | An approved outside organisation, such as an employer. Sends verification requests only. |

Students are not users in v1. Consent is recorded through the institution.

## What each role can do

| Capability | AICTE_ADMIN | AICTE_OFFICER | INSTITUTION_ADMIN | INSTITUTION_STAFF | VERIFIER |
|---|---|---|---|---|---|
| Upload records (file or API) | No | No | Own institution | Own institution | No |
| Correct or withdraw records | Any (built in Phase 4) | No | Own institution | Own institution | No |
| List records | All | Own regions | Own institution | Own institution | No |
| View one record (audited) | All | Own regions | Own institution | Own institution | No |
| Answer flags on own records (reply to an ask) | No | No | Yes | Yes | No |
| Review, resolve, dismiss flags | All | Own regions | No | No | No |
| Run, save and export reports | Yes | Yes | No | No | No |
| View dashboards | All | Own regions | Own institution | Own institution | No |
| Edit rules, diff, revert | Yes | No | No | No | No |
| Edit purpose policies | Yes | No | No | No | No |
| Approve or reject verifiers | Yes | No | No | No | No |
| Manage users (any role except verifier), regions, windows, clock | Yes | No | No | No | No |
| Read and verify the audit log | Yes | No | No | No | No |
| Record or withdraw consent | No | No | Own students | Own students | No |
| Manage API keys | No | No | Own institution | No | No |
| Manage staff accounts (staff role only: create, rename, deactivate, reset password) | No | No | Own institution | No | No |
| Verification requests | View all | Scope not set | View requests about own students | View requests about own students | Create (approved only), view own |
| Send a verification request | No | No | No | No | Approved verifiers only |

Notes:

- A `PENDING` verifier can register and log in, but cannot send requests.
- Nothing in this table is protected by hiding a menu item. The server checks each request.

## Object-level scope

Role alone is not enough. Services also check the object.

| Object | Check |
|---|---|
| Student record, upload, flag on an institution's record | The record's institution must be the user's institution. Otherwise, a plain refusal. The refusal is audited. |
| Records and flags for AICTE officers | The institution's region must be in `user_region`. |
| Records and flags for AICTE admins | No region limit. |
| API key | Works only for its own institution, and only with scope `records:submit`. Revoked keys are refused. |
| Verification request | The verifier sees only its own requests. |
| Verification result | Only the fields that the consent and the purpose policy allow. |
| Consent | Only the institution that holds the student's record can record or withdraw it. |
| Notifications | Only the recipient sees a notification. |

The plan requires a test for each of these: "an institution user must not read another institution's records or flags", "a verifier must not see anything that the consent did not cover", and "a regional officer must not see another region."

## Masking

Student fields are masked in the API serializer for every viewer. Masking is done by `masking.serialize_record(record, viewer)`.

| Field | Shown in full to | Shown masked to |
|---|---|---|
| APAAR ID | The record's own institution, AICTE officers and admins | Everyone else. Shown as `XXXX XXXX 1234`. |
| Name, date of birth | The record's own institution, AICTE officers and admins | Everyone else |
| Other fields (programme, year, admission details) | Shown as the role allows | Shown as the role allows |

A verifier sees only the fields the consent allows, and nothing more.

Outside-reader reports leave out identity fields altogether.

## Open questions

- **Cross-institution alerts (R05).** The idea doc's example names both colleges in the alert. Should an institution see the other institution's name and programme? Should it see the full APAAR ID? The plan does not say. Decide before Phase 3.
- **AICTE officer and verification log.** The nav gives officers the verifications page. The plan does not say which requests an officer may see.
- **Institution admin and staff on consent.** The plan says consent is recorded "through the institution". It does not say whether staff can withdraw consent as well as admins.


## Phase 6 decisions on the open questions (built in the backend)

- **Officer and the verification log:** an officer sees verification requests about students of their regions (precise refusal reasons included). Admin sees all.
- **Consent withdrawal:** institution admin and staff may both record and withdraw consent for students at their institution; AICTE admin for any student. Officers cannot record or withdraw.
- **Verifier:** sees only their own requests, with the generic refusal for anything that depends on a student or consent (ADR-021). Approval is per purpose.
