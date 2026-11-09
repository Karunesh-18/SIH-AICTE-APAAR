# API outline

Last updated: 2026-11-09.

**Status: the endpoints in the "Built" table below are in the code and tested. Every other endpoint in this file is PROPOSED.** The plan names the actions. The exact paths below are our wording. Where the built path differs from the plan, the built path wins and the row says so.

## Built (Phase 1)

| Method | Path | Who | Purpose | Audit |
|---|---|---|---|---|
| GET | `/health` | Public | Liveness check. Outside `/api/v1`. | No |
| POST | `/api/v1/auth/login` | Anyone | Access and refresh tokens. Rate limited per email (in memory). | Yes (`AUTH.LOGIN`) |
| POST | `/api/v1/auth/refresh` | Signed-in user | New access token | No |
| GET | `/api/v1/auth/me` | Signed-in user | Current user, role and scope. Plan name was `/api/v1/me`. | No |
| PATCH | `/api/v1/auth/me` | Signed-in user | Change own language (`en` or `hi`). Plan name was `/api/v1/me`. | Yes (`USER.LANGUAGE`) |
| GET | `/api/v1/institutions` | Signed-in user, scoped by role and region | List institutions in scope | No |
| GET | `/api/v1/institutions/{id}` | Signed-in user, scoped | One institution. Out of scope gives 403. | Refusals only (`ACCESS.REFUSED`) |
| GET | `/api/v1/admin/audit` | AICTE admin | Paginated audit log (`limit`, `offset`). Plan name was `/api/v1/audit`. | No |
| POST | `/api/v1/admin/audit/verify` | AICTE admin | Walk the hash chain. Returns ok, or the first broken ID. Plan name was `/api/v1/audit/verify`. | No |
| POST | `/api/v1/admin/dev/tamper-audit` | AICTE admin, demo mode only (404 otherwise) | Edits one audit row on purpose. Plan name was `/api/v1/dev/tamper-audit`. | No (raw edit on purpose) |
| GET | `/api/v1/admin/clock` | AICTE admin | Clock offset in days, and now | No |
| POST | `/api/v1/admin/clock` | AICTE admin | Advance by `advance_days`, or `reset`. Saved in `system_config`. The plan said PUT. | Yes (`CLOCK.SET`) |
| GET | `/api/v1/notifications` | Signed-in user (own). `?unread` filter. | In-app notifications | No |
| POST | `/api/v1/notifications/{id}/read` | Signed-in user (own). 404 for other users' IDs. | Mark one as read | Yes (`NOTIFICATION.READ`) |

Every built route appears in `backend/tests/test_permission_matrix.py`. A test fails if a new `/api/v1` route is not listed there (ADR-007).

The Phase 1 frontend and the Phase 2 data work added no endpoints. The frontend calls the routes above.

## Conventions

- Base path: `/api/v1`.
- JSON in and out. Multipart for file upload.
- Pydantic v2 models with `extra="forbid"`. Unknown fields are refused.
- Auth: short-lived access token and a longer refresh token (JWT, HS256). Institutions can also send data with a per-institution API key that has scope `records:submit`.
- Every route checks the role on the server. Services check the object scope too (see `ROLES.md`).
- CORS: the API allows only the origins in `cors_origins` (default `http://localhost:3000`). Other origins get no `Access-Control-Allow-Origin` header. Test: `backend/tests/test_health.py`.
- The API documents itself through the OpenAPI page that FastAPI generates.
- Status codes and the error body format are not set in the plan.

### Audit column

The audit column follows the plan's audit scope:

- **Yes**: writes, single-record views, exports, verifications and refusals are audited.
- **No**: list and dashboard reads are not audited.
- **Not set**: the plan does not say.

### Route order

`GET /verify/public-key` must be declared before `GET /verify/{token}`. Otherwise `public-key` is read as a token.

### Differences from the idea doc

The idea doc (section 18) gives some different paths. The plan replaces them:

| Idea doc | This file (from the plan) |
|---|---|
| `GET /audit/verify` | `POST /api/v1/audit/verify` |
| `PUT /admin/rules/{code}` | `PUT /api/v1/admin/rules/{code}` creates a new version, and there are version, diff and revert routes |
| Separate history endpoints | Record history comes back with `GET /api/v1/records/{id}` |

## Auth and profile

| Method | Path | Who | Purpose | Audit |
|---|---|---|---|---|
| POST | `/api/v1/auth/login` | Anyone | Get access and refresh tokens. **BUILT.** | Yes (`AUTH.LOGIN`) |
| POST | `/api/v1/auth/refresh` | Signed-in user | Get a new access token | Not set |
| GET | `/api/v1/me` | Signed-in user | Current user, role and scope. **BUILT** as `/api/v1/auth/me`. | No |
| PATCH | `/api/v1/me` | Signed-in user | Change own language (`en` or `hi`). **BUILT** as `/api/v1/auth/me`. | Yes |

## Uploads and submissions

| Method | Path | Who | Purpose | Audit |
|---|---|---|---|---|
| POST | `/api/v1/uploads` | Institution admin or staff (own institution) | Multipart file upload. Returns a receipt with the upload ID straight away. Checks run in the background. | Yes |
| GET | `/api/v1/uploads/{id}` | Institution (own), AICTE (in scope) | Result page. Counts, flags, and status while checks run. | Not set |
| GET | `/api/v1/templates/csv` and `/api/v1/templates/xlsx` | Signed-in user | Download the template | No |
| POST | `/api/v1/institutions/{id}/students` | API key with `records:submit`, or institution admin or staff | JSON batch. Same checks as the file upload. | Yes |

## Records

| Method | Path | Who | Purpose | Audit |
|---|---|---|---|---|
| GET | `/api/v1/institutions/{id}/records` | Institution (own). AICTE (in region). | List records | No |
| GET | `/api/v1/records/{id}` | Institution (own). AICTE (in region or all, by role). | One record, with its history | Yes |
| PATCH | `/api/v1/records/{id}` | Institution admin or staff (own) | Correction. Creates a new version. | Yes |
| POST | `/api/v1/records/{id}/withdraw` | Institution admin or staff (own) | Withdraw with a reason. Record stays in history. | Yes |

## Flags

| Method | Path | Who | Purpose | Audit |
|---|---|---|---|---|
| GET | `/api/v1/flags` | Scoped by role. Filters: `state`, `rule`, `institution`, `region`, `age`. | Queue | No |
| GET | `/api/v1/flags/{id}` | Scoped by role | One flag, with its evidence | Not set |
| POST | `/api/v1/flags/{id}/review` | AICTE officer (in region) or admin | Move to `under_review`. Note required. | Yes |
| POST | `/api/v1/flags/{id}/resolve` | AICTE officer (in region) or admin | Resolve. Note required. | Yes |
| POST | `/api/v1/flags/{id}/dismiss` | AICTE officer (in region) or admin | Dismiss. Note required. | Yes |
| POST | `/api/v1/flags/{id}/ask` | AICTE officer or admin | Ask the institution. Note required. | Yes |
| POST | `/api/v1/flags/{id}/link` | AICTE officer or admin | Link near-duplicate records (R08). Note required. | Yes |

Institution users answer flags on their own records. The plan does not say which of these actions they may use.

## Dashboards

| Method | Path | Who | Purpose | Audit |
|---|---|---|---|---|
| GET | `/api/v1/dashboards/aicte` | AICTE roles, scoped by region | Summary tiles and institution table | No |
| GET | `/api/v1/dashboards/institution` | Institution (own) | Own submission status | No |
| GET | `/api/v1/dashboards/intake-use` | AICTE roles, scoped by region | Intake use by programme | No |

## Reports

| Method | Path | Who | Purpose | Audit |
|---|---|---|---|---|
| GET | `/api/v1/reports` | AICTE officer or admin | List saved report definitions | No |
| POST | `/api/v1/reports` | AICTE officer or admin | Save a report definition | Yes |
| GET | `/api/v1/reports/{name}?format=csv` | AICTE officer or admin | Run and export. Outside-reader reports leave out identity fields. | Yes |

## Consent

| Method | Path | Who | Purpose | Audit |
|---|---|---|---|---|
| POST | `/api/v1/consents` | Institution admin or staff (own students) | Record consent, with purpose, fields, source and expiry | Yes |
| DELETE | `/api/v1/consents/{id}` | Institution admin or staff (own students) | Withdraw consent | Yes |
| GET | `/api/v1/consents?apaar={id}` | Institution (own students). AICTE scope not set. | List consent for an APAAR ID | No |

## Verifiers

| Method | Path | Who | Purpose | Audit |
|---|---|---|---|---|
| POST | `/api/v1/verifiers/register` | Public | Register. Creates a `PENDING` verifier. | Yes |
| POST | `/api/v1/admin/verifiers/{id}/approve` | AICTE admin | Approve. Note required. | Yes |
| POST | `/api/v1/admin/verifiers/{id}/reject` | AICTE admin | Reject. Note required. | Yes |

## Verification

| Method | Path | Who | Purpose | Audit |
|---|---|---|---|---|
| POST | `/api/v1/verifications` | Approved verifier | Send an APAAR ID and a purpose. Returns an allowed result with a signed token, or a refusal. | Yes (verification or refusal) |
| GET | `/api/v1/verifications/{id}` | Verifier (own), institution (own students), AICTE admin | One request and its outcome | Yes |
| GET | `/api/v1/verifications` | Scoped by role | List requests | No |
| GET | `/api/v1/verify/public-key` | Public | Ed25519 public key for checking tokens | No |
| GET | `/api/v1/verify/{token}` | Public | Checks a token: genuine, expired, revoked or tampered | Yes (verification) |

## Notifications

| Method | Path | Who | Purpose | Audit |
|---|---|---|---|---|
| GET | `/api/v1/notifications` | Signed-in user (own). Polled by the bell. **BUILT.** | List own notifications | No |
| POST | `/api/v1/notifications/{id}/read` | Signed-in user (own). **BUILT.** | Mark one as read. Not in the plan; added in Phase 1. | Yes |

## Admin

| Method | Path | Who | Purpose | Audit |
|---|---|---|---|---|
| GET | `/api/v1/admin/rules` | AICTE admin | List rules and their active versions | No |
| GET | `/api/v1/admin/rules/{code}/versions` | AICTE admin | Version history of one rule | No |
| PUT | `/api/v1/admin/rules/{code}` | AICTE admin | Change a rule. Creates a new version. | Yes |
| GET | `/api/v1/admin/rules/{code}/diff` | AICTE admin | Compare two versions | No |
| POST | `/api/v1/admin/rules/{code}/revert` | AICTE admin | Copy an old version into a new version | Yes |
| GET, PUT | `/api/v1/admin/policies` and `/api/v1/admin/policies/{purpose}` | AICTE admin | Purpose policies and their field allow-lists | Yes (writes) |
| GET, POST, PATCH | `/api/v1/admin/users` | AICTE admin | Users | Yes (writes) |
| GET, POST, PATCH | `/api/v1/admin/regions` | AICTE admin | Regions | Yes (writes) |
| GET, POST, PATCH | `/api/v1/admin/windows` | AICTE admin | Submission windows and their ladders | Yes (writes) |
| GET, POST | `/api/v1/admin/clock` | AICTE admin | Read or set the clock offset. **BUILT** with POST (plan said PUT). | Yes (writes) |
| POST | `/api/v1/admin/alert-cycle` | AICTE admin | Run the reminder cycle now | Yes |
| GET | `/api/v1/admin/audit` | AICTE admin | Read the audit log. **BUILT** at this path. | No |
| POST | `/api/v1/admin/audit/verify` | AICTE admin | Walk the chain. Returns ok, or the first broken ID. **BUILT** at this path. | No |
| POST | `/api/v1/admin/dev/tamper-audit` | AICTE admin, demo mode only | Changes one audit row on purpose, to show the check. **BUILT** at this path. | No (raw edit on purpose) |

## Institution admin

| Method | Path | Who | Purpose | Audit |
|---|---|---|---|---|
| GET, POST | `/api/v1/institution/api-keys` | Institution admin (own) | List keys and create one. The key is shown once. | Yes (writes) |
| POST | `/api/v1/institution/api-keys/{id}/revoke` | Institution admin (own) | Revoke a key | Yes |
| GET, POST, PATCH | `/api/v1/institution/staff` | Institution admin (own) | Staff accounts | Yes (writes) |

Every use of an API key is audited, not only creating and revoking it.


## Phase 3 as built (backend)

- `POST /uploads` (multipart `file`, `cycle_year`, `institution_id` for AICTE roles) returns 202 `{id, status, row_count: null}`. Processing runs in a FastAPI background task. `GET /uploads/{id}` returns status, counts, `flags {total, by_rule}` and the rejection message. `GET /uploads` lists in scope (`items`, `total`).
- A whole upload is `REJECTED` only when it is empty, unreadable, lacks required columns, or the programme cannot be told. Nothing but the upload row is stored then. `accepted_count` is the rows stored (nothing is dropped); `flagged_count` is distinct rows touched by a flag.
- `GET /institutions/{id}/records?status=&limit=&offset=` lists current records. `GET /records/{id}` is audited (`RECORD.VIEWED`) and returns version history and flags. Name, date of birth and APAAR ID are masked for outside readers in the serializer.
- `POST /institutions/{id}/students` takes `{cycle_year, students: [...]}` with a JWT or `X-API-Key`. It processes synchronously and returns the upload summary.
- `POST/GET /institutions/{id}/api-keys`, `DELETE .../{key_id}` (revoke). Institution admin of that institution or AICTE admin. The token is returned once.
- `GET /uploads/{id}` also returns `flag_items` (rule code, reason, evidence, listed row numbers) so the receipt page can explain each flag.
- `/admin/rules`, `/admin/rules/{code}/versions`, `PUT /admin/rules/{code}`, `/admin/rules/{code}/diff?from=&to=`, `POST /admin/rules/{code}/revert`. AICTE admin only. A note is required to change or revert.
