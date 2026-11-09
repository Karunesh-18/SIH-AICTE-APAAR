// Offline check of a signed QR token: Ed25519 signature only, no network. Revocation needs the API.
const KEY = "waymark.publicKey";

export type OfflineResult = { valid: boolean; expired: boolean; claims?: object; reason?: string };

const bad = (reason: string): OfflineResult => ({ valid: false, expired: false, reason });
const dec = (s: string) => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0));
const json = (s: string) => JSON.parse(new TextDecoder().decode(dec(s)));

export async function verifyOffline(token: string, jwk: JsonWebKey): Promise<OfflineResult> {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return bad("format");
    const [h, p, s] = parts;
    const header = json(h);
    const claims = json(p);
    if (header.alg !== "EdDSA") return bad("format");
    if (header.kid && (jwk as { kid?: string }).kid && header.kid !== (jwk as { kid?: string }).kid) return bad("key");
    const key = await crypto.subtle.importKey("jwk", jwk, { name: "Ed25519" }, false, ["verify"]);
    const ok = await crypto.subtle.verify("Ed25519", key, dec(s), new TextEncoder().encode(`${h}.${p}`));
    if (!ok) return bad("signature");
    // The client clock decides expiry here; the server clock (or demo clock) is not available offline.
    const expired = typeof claims.exp === "number" && claims.exp * 1000 < Date.now();
    return { valid: true, expired, claims, ...(expired && { reason: "expired" }) };
  } catch {
    return bad("format");
  }
}

export function cacheKey(jwk: JsonWebKey): void {
  try { localStorage.setItem(KEY, JSON.stringify(jwk)); } catch { /* private window: no cache */ }
}

export function cachedKey(): JsonWebKey | null {
  try {
    const v = localStorage.getItem(KEY);
    return v ? JSON.parse(v) : null;
  } catch { return null; }
}
