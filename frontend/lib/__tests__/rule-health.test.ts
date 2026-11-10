import { describe, expect, it } from "vitest";
import { dash, healthShare, oftenDismissed } from "../rules";

const h = (resolved: number, dismissed: number) => ({ resolved, dismissed });

describe("oftenDismissed", () => {
  it("needs a share of at least half and at least 5 closed", () => {
    expect(oftenDismissed({ ...h(2, 3), dismissed_share: 0.6 })).toBe(true);
    expect(oftenDismissed({ ...h(3, 3), dismissed_share: 0.5 })).toBe(true);
  });
  it("not with fewer than 5 closed or a low share", () => {
    expect(oftenDismissed({ ...h(0, 4), dismissed_share: 1 })).toBe(false);
    expect(oftenDismissed({ ...h(4, 2), dismissed_share: 0.33 })).toBe(false);
    expect(oftenDismissed({ ...h(0, 0), dismissed_share: null })).toBe(false);
  });
});

describe("dash and healthShare", () => {
  it("shows a dash for null", () => {
    expect(dash(null)).toBe("-");
    expect(healthShare(null)).toBe("-");
  });
  it("formats a share as a whole percent", () => expect(healthShare(2 / 3)).toBe("67%"));
  it("keeps zero", () => expect(dash(0)).toBe("0"));
});
