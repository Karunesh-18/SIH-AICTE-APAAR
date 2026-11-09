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
