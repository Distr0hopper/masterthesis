import { describe, expect, it } from 'vitest';
import { isTokenExpired, readTokenTimes } from '@/lib/jwt';
import { isDueForRefresh, loginPath, safeRedirect } from './session';

const HOUR = 60 * 60 * 1000;
const NOW = Date.UTC(2026, 8, 27, 12, 0, 0);

/** an unsigned token with the given iat/exp - the frontend never checks the signature */
function token(issuedAt: number, expiresAt: number): string {
  const encode = (value: object) => btoa(JSON.stringify(value)).replace(/=+$/, '');
  return `${encode({ alg: 'HS256' })}.${encode({ sub: 'u', iat: issuedAt / 1000, exp: expiresAt / 1000 })}.sig`;
}

describe('readTokenTimes / isTokenExpired', () => {
  it('reads iat and exp in milliseconds', () => {
    expect(readTokenTimes(token(NOW, NOW + 24 * HOUR))).toEqual({ issuedAt: NOW, expiresAt: NOW + 24 * HOUR });
  });

  it('treats a token as expired once exp has passed', () => {
    const t = token(NOW - 24 * HOUR, NOW);
    expect(isTokenExpired(t, NOW - HOUR)).toBe(false);
    expect(isTokenExpired(t, NOW + 1)).toBe(true);
  });

  it('treats an unreadable token as expired', () => {
    expect(isTokenExpired('not-a-jwt', NOW)).toBe(true);
  });
});

describe('isDueForRefresh', () => {
  const t = token(NOW, NOW + 24 * HOUR);

  it('is not due during the first hour', () => {
    expect(isDueForRefresh(t, NOW + 30 * 60 * 1000)).toBe(false);
  });

  it('is due after an hour - so yesterday evening still carries into the next morning', () => {
    expect(isDueForRefresh(t, NOW + HOUR)).toBe(true);
  });

  it('renews short-lived tokens at half-life instead', () => {
    const short = token(NOW, NOW + 10 * 60 * 1000);
    expect(isDueForRefresh(short, NOW + 4 * 60 * 1000)).toBe(false);
    expect(isDueForRefresh(short, NOW + 5 * 60 * 1000)).toBe(true);
  });
});

describe('safeRedirect / loginPath', () => {
  it('keeps paths inside the app', () => {
    expect(safeRedirect('/my-components?offset=10')).toBe('/my-components?offset=10');
  });

  it('rejects other origins and the login page itself', () => {
    expect(safeRedirect('https://evil.example')).toBeNull();
    expect(safeRedirect('//evil.example/path')).toBeNull();
    expect(safeRedirect('/login?redirect=/x')).toBeNull();
    expect(safeRedirect(null)).toBeNull();
  });

  it('builds the login URL with where to return and why', () => {
    expect(loginPath({ redirect: '/my-components', expired: true })).toBe(
      '/login?redirect=%2Fmy-components&reason=expired',
    );
    expect(loginPath({ redirect: '//evil.example' })).toBe('/login');
    expect(loginPath()).toBe('/login');
  });
});
