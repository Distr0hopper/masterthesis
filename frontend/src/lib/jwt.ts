/**
 * Reading our own access token's timestamps. The signature is not checked here - that's
 * the backend's job; the frontend only needs to know *when* the token stops working.
 */

export interface TokenTimes {
  /** ms since epoch */
  issuedAt: number;
  /** ms since epoch */
  expiresAt: number;
}

/** allowance for the clock difference between browser and server */
const CLOCK_SKEW_MS = 10_000;

export function readTokenTimes(token: string): TokenTimes | null {
  try {
    const payload = token.split('.')[1];
    const json = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
    if (typeof json.exp !== 'number' || typeof json.iat !== 'number') return null;
    return { issuedAt: json.iat * 1000, expiresAt: json.exp * 1000 };
  } catch {
    return null;
  }
}

/** A token that can't be read counts as expired - it would be rejected anyway. */
export function isTokenExpired(token: string, now = Date.now()): boolean {
  const times = readTokenTimes(token);
  return times === null || now >= times.expiresAt - CLOCK_SKEW_MS;
}
