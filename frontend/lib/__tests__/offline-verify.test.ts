import { describe, expect, it } from "vitest";
import { verifyOffline } from "../offline-verify";

const b64u = (b: ArrayBuffer | string) =>
  Buffer.from(typeof b === "string" ? b : new Uint8Array(b)).toString("base64url");

async function pair() {
  const kp = (await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"])) as CryptoKeyPair;
  const jwk = { ...(await crypto.subtle.exportKey("jwk", kp.publicKey)), kid: "k1", alg: "EdDSA" };
  return { priv: kp.privateKey, jwk };
}
async function sign(priv: CryptoKey, claims: object, header: object = { alg: "EdDSA", typ: "JWT", kid: "k1" }) {
  const body = `${b64u(JSON.stringify(header))}.${b64u(JSON.stringify(claims))}`;
  return `${body}.${b64u(await crypto.subtle.sign("Ed25519", priv, new TextEncoder().encode(body)))}`;
}
const future = Math.floor(Date.now() / 1000) + 3600;

describe("verifyOffline", () => {
  it("accepts a valid token", async () => {
    const { priv, jwk } = await pair();
    const r = await verifyOffline(await sign(priv, { sub: "a", exp: future }), jwk);
    expect(r).toMatchObject({ valid: true, expired: false, claims: { sub: "a" } });
  });
  it("rejects a payload altered by one character", async () => {
    const { priv, jwk } = await pair();
    const [h, p, s] = (await sign(priv, { sub: "a", exp: future })).split(".");
    const r = await verifyOffline(`${h}.${p.slice(0, -2)}${p.at(-2) === "A" ? "B" : "A"}${p.at(-1)}.${s}`, jwk);
    expect(r.valid).toBe(false);
    expect(r.reason).toBeTruthy();
  });
  it("flags an expired token as valid-signature but expired", async () => {
    const { priv, jwk } = await pair();
    const r = await verifyOffline(await sign(priv, { exp: 1 }), jwk);
    expect(r).toMatchObject({ valid: true, expired: true });
  });
  it("rejects a token signed by a different key", async () => {
    const a = await pair();
    const b = await pair();
    const r = await verifyOffline(await sign(a.priv, { exp: future }), b.jwk);
    expect(r.valid).toBe(false);
  });
  it("rejects a kid mismatch and a wrong alg", async () => {
    const { priv, jwk } = await pair();
    expect((await verifyOffline(await sign(priv, { exp: future }, { alg: "EdDSA", kid: "other" }), jwk)).valid).toBe(false);
    expect((await verifyOffline(await sign(priv, { exp: future }, { alg: "HS256", kid: "k1" }), jwk)).valid).toBe(false);
  });
  it("never throws on malformed input", async () => {
    const { jwk } = await pair();
    for (const t of ["", "abc", "a.b.c", "a.b", "....", "%%.%%.%%"]) {
      const r = await verifyOffline(t, jwk);
      expect(r.valid).toBe(false);
      expect(r.reason).toBeTruthy();
    }
  });
});
