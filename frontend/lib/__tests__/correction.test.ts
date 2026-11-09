import { describe, expect, it } from "vitest";
import { buildCorrection } from "../correction";

const empty = { apaar_id: "", name: "", dob: "", year_of_study: "", admission_date: "", admission_category: "" };
describe("buildCorrection", () => {
  it("returns null when nothing is filled", () => expect(buildCorrection(empty)).toBeNull());
  it("sends only filled fields, trimmed, year as a number", () =>
    expect(buildCorrection({ ...empty, apaar_id: " 999912345678 ", year_of_study: "2" }))
      .toEqual({ apaar_id: "999912345678", year_of_study: 2 }));
  it("ignores a non-numeric year", () => expect(buildCorrection({ ...empty, year_of_study: "x" })).toBeNull());
});
