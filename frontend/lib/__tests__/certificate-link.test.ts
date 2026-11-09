import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

describe("certificate entry point", () => {
  it("record detail links to the certificate view", () => {
    const src = readFileSync("app/(app)/institution/records/[id]/page.tsx", "utf8");
    expect(src).toContain("/certificate");
    expect(src).toContain('t("cert.open")');
  });
});
