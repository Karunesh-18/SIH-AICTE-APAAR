import { describe, expect, it } from "vitest";
import en from "../i18n/en.json";
import hi from "../i18n/hi.json";

// Scalar evidence keys emitted by backend/app/domain/rules.py (R01-R08), rules_scheduled.py
// (R09-R12) and services/anomaly.py (cycle_year on scheduled flags).
const EVIDENCE_KEYS = [
  "found", "expected_digits", "checksum", "digits_found", "apaar_id", "submitted", "registry",
  "similarity", "threshold", "count", "approved_intake", "supernumerary_seats", "allowed",
  "actual", "excess", "admission_date", "cycle_year", "ids", "score", "closed_at", "current",
  "previous", "rise_pct", "limit_pct", "pending", "total", "share_pct", "rows", "last_hours",
  "bulk_rows", "uploaded_at", "top_category", "top_share_pct", "reason", "deviation", "limit",
];

describe("evidence labels", () => {
  for (const [lang, dict] of [["en", en], ["hi", hi]] as const) {
    it(`${lang} has a label for every backend evidence key`, () => {
      const d = dict as Record<string, string>;
      expect(EVIDENCE_KEYS.filter((k) => !d[`ev.${k}`]?.trim())).toEqual([]);
    });
  }
});
