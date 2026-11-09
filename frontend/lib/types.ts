export type RecordStatus = "submitted" | "valid" | "flagged" | "pending_apaar" | "withdrawn";
export type Page<T> = { items: T[]; total: number };

export type FlagItem = {
  id: string; rule_code: string; reason_key: string; reason: string;
  evidence: Record<string, unknown>; rows: number[];
};
export type Upload = {
  id: string; institution_id: string; cycle_year: number; source: string; format: string;
  status: "RECEIVED" | "PROCESSING" | "DONE" | "REJECTED" | string;
  row_count: number | null; accepted_count: number; flagged_count: number;
  error: string | null; created_at: string;
  flags: { total: number; by_rule: Record<string, number> };
  flag_items?: FlagItem[];
};
export type UploadReceipt = { id: string; status: string; row_count: number | null };

export type RecordRow = {
  id: string; apaar_id: string | null; name: string; dob: string; programme: string;
  cycle_year: number; year_of_study: number | null; admission_date: string;
  admission_category: string | null; nri: boolean; oci: boolean; fn: boolean;
  status: RecordStatus; version: number; is_current: boolean; upload_id: string; row_number: number;
};
export type RecordDetail = RecordRow & {
  versions: { id: string; version: number; is_current: boolean; upload_id: string; status: string; superseded_at: string | null }[];
  flags: { id: string; rule_code: string; state: string; reason: string; evidence: Record<string, unknown> }[];
};

export type ApiKey = {
  id: string; name: string; prefix: string; scope: string;
  created_at: string; last_used_at: string | null; revoked_at: string | null;
};
export type NewApiKey = ApiKey & { key: string };

export type RuleVersion = {
  id: string; rule_code: string; version_no: number; enabled: boolean;
  params: Record<string, unknown>; hard_stop: boolean; message_en: string; message_hi: string | null;
  note: string | null; is_active: boolean; created_by: string | null; created_at: string;
};
export type RuleSummary = { code: string; scope: string; title: string; active: RuleVersion | null };

export type FlagRow = {
  id: string; rule_code: string; reason_key: string; reason: string; state: string;
  institution_id: string; institution_name: string; assignee_id: string | null; upload_id: string;
  lock_version: number; record_count: number; created_at: string; age_days: number;
};
export type FlagEvent = {
  id: string; from_state: string | null; to_state: string; note: string | null; at: string;
  actor_id: string | null; actor_name: string; actor_role: string | null;
};
export type FlagDetail = FlagRow & {
  evidence: Record<string, unknown>;
  rule_version: { id: string; rule_code: string; version_no: number; params: Record<string, unknown>; message_en: string; hard_stop: boolean };
  records: RecordRow[];
  events: FlagEvent[];
};
export type FlagBrief = { id: string; rule_code: string; reason: string; state: string };
export type CorrectionResult = { record: RecordRow; previous: RecordRow; closed_flags: FlagBrief[]; raised_flags: FlagBrief[] };
export type Notification = {
  id: string; subject: string; body: string; related_type: string | null; related_id: string | null;
  read_at: string | null; created_at: string;
};

export type InstState = "Clear" | "Alert" | "Excess";
export type DashInstitution = {
  id: string; name: string; type: string; region: string; region_code: string; state: InstState;
  enrolled: number; approved_intake: number; allowed: number; flags: Record<string, number>;
  open_flags: number; last_upload: string | null;
};
export type AicteDashboard = {
  cycle_year: number;
  tiles: { institutions: number; records: number; open_flags: number; excess: number; alert: number; pending_apaar_share: number };
  institutions: DashInstitution[];
};
export type RegionRow = { id: string; code: string; name: string };
export type InstitutionRow = { id: string; name: string; type?: string; region_id?: string };
export type ProgrammeRow = {
  institution_id: string; institution: string; region: string; institution_type: string; programme: string;
  level: string; enrolled: number; approved_intake: number; allowed: number;
};
export type FlagsTrend = { rows: { month: string; rule: string; count: number }[] };
export type WindowStatus = {
  cycle_year: number; opens_at: string; closes_at: string; state: "not_open" | "open" | "closed";
  submitted: boolean; hours_to_close: number;
} | null;
export type TodoFlag = { id: string; rule: string; reason: string; state: string };
export type InstitutionDashboard = {
  institution: { id: string; name: string }; cycle_year: number; window: WindowStatus; submitted: boolean;
  records: { accepted: number; flagged: number; pending_apaar: number };
  todo: { open_flags: TodoFlag[]; asks: TodoFlag[]; pending_apaar: { record_id: string; row_number: number }[] };
};
export type ReportDef = { key: string; title: string; filters: string[] };
export type SavedReport = { id: string; name: string; report_key: string; filters: Record<string, string | number>; created_at: string };
export type ReportResult = { columns?: string[]; rows?: Record<string, unknown>[] } & Record<string, unknown>;
export type AdminWindow = {
  id: string; cycle_year: number; institution_type: string | null; opens_at: string; closes_at: string;
  ladder: { step: string; offset_hours: number; audience: "institution" | "officer" | "admin" }[];
};
export type CycleResult = { sent: number; skipped: number; late: string[]; flags: number; windows: number };
export type ClockState = { offset_days: number; now: string; demo_mode?: boolean };

// Phase 6: consent and verification
export type PolicyRead = { purpose: string; allowed_fields: string[]; version: number };
export type PolicyAdmin = PolicyRead & { note: string | null; updated_at: string };
export type Policies<P = PolicyRead> = { items: P[]; fields: string[] };
export type Consent = {
  id: string; apaar_id: string; purposes: string[]; fields: string[]; source: string;
  given_at: string; expires_at: string; withdrawn_at: string | null;
};
export type VerifierReg = {
  id: string; org_name: string; org_type: string; contact: string; email: string;
  requested_purposes: string[]; status: "PENDING" | "APPROVED" | "REJECTED";
  decided_by: string | null; decision_note: string | null; created_at: string;
};
export type VerificationRow = {
  id: string; outcome: "GRANTED" | "REFUSED"; purpose: string; apaar_id: string;
  fields_requested: string[]; refusal_reason: string | null; refusal_detail: string[] | null;
  issued_at: string | null; expires_at: string | null; revoked_at: string | null; created_at: string;
  verifier?: string; consent_id?: string | null;
};
export type VerificationGranted = {
  id: string; outcome: "GRANTED"; purpose: string; fields: Record<string, unknown>; token: string;
  qr_url: string; issued_at: string; expires_at: string;
};
export type VerificationRefused = {
  id: string; outcome: "REFUSED"; reason: string; message: string; detail?: string[];
};
export type VerificationResult = VerificationGranted | VerificationRefused;
export type PublicCheck = {
  status: string; fields: Record<string, unknown> | null; issuer: string | null;
  issued_at: string | null; expires_at: string | null; purpose: string | null;
};
export type PublicKey = { pem: string; jwk: { kid: string; x: string; alg: string }; alg: string };
export type AuditRow = {
  id: number; occurred_at: string; actor_id: string | null; actor_role: string | null; action: string;
  entity_type: string | null; entity_id: string | null; before: unknown; after: unknown;
};

export type Checkpoint = { seq: number; hash: string; count: number; signed_at: string; token: string };
export type CheckpointCheck = { ok: boolean; reason: "missing_rows" | "hash_mismatch" | "bad_signature" | null };

export type UserRow = {
  id: string; email: string; full_name: string; role: string; institution_id: string | null;
  institution_name: string | null; is_active: boolean; language: string; regions: string[];
};
export type UserList = { items: UserRow[]; total: number };
export type UserSaved = { user: UserRow; temporary_password?: string };
