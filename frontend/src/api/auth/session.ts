import axios from 'axios';
import { toast } from 'sonner';
import { useAuthStore } from '@/store/auth.store';
import { isTokenExpired, readTokenTimes } from '@/lib/jwt';
import { ROUTES } from '@/lib/routes';
import type { AuthResponseDto } from './types';

/**
 * The sliding session. A token lives JWT_EXPIRES_IN (24h) from when it was issued; while
 * the user is active it is swapped for a fresh one, so a session only ends after a full
 * lifetime *without activity*. "Activity" is an API request or returning to the tab -
 * never a timer, or a tab left open would keep the session alive forever.
 */

/** renew once the token is this old - early enough that yesterday evening's work still
 *  carries you into the next morning, rare enough to be at most one request an hour */
const REFRESH_AFTER_MS = 60 * 60 * 1000;

let refreshing: Promise<void> | null = null;

export function isDueForRefresh(token: string, now = Date.now()): boolean {
  const times = readTokenTimes(token);
  if (!times) return false;
  const lifetime = times.expiresAt - times.issuedAt;
  // for short lifetimes (tests, a lowered JWT_EXPIRES_IN), renew at half-life instead
  return now - times.issuedAt >= Math.min(REFRESH_AFTER_MS, lifetime / 2);
}

/** Swaps a still-valid, due token for a fresh one - fire and forget, one request at a time. */
export function refreshSessionIfDue(): void {
  const token = useAuthStore.getState().token;
  if (!token || refreshing || isTokenExpired(token) || !isDueForRefresh(token)) return;

  // plain axios, not apiClient: its interceptor calls back into this function
  refreshing = axios
    .post<AuthResponseDto>(`${import.meta.env.VITE_API_BASE_URL}/auth/refresh`, null, {
      headers: { Authorization: `Bearer ${token}` },
    })
    .then(({ data }) => {
      // only if nobody logged out or in meanwhile
      if (useAuthStore.getState().token === token) useAuthStore.getState().setToken(data.accessToken);
    })
    .catch(() => {
      // harmless: the current token keeps working until it expires, and the next
      // activity tries again
    })
    .finally(() => {
      refreshing = null;
    });
}

export function currentPath(): string {
  return window.location.pathname + window.location.search;
}

/** `/login`, remembering where to go back to - and optionally why the user is there. */
export function loginPath(options: { redirect?: string; expired?: boolean } = {}): string {
  const params = new URLSearchParams();
  const redirect = safeRedirect(options.redirect ?? null);
  if (redirect) params.set('redirect', redirect);
  if (options.expired) params.set('reason', 'expired');
  const query = params.toString();
  return query ? `${ROUTES.login}?${query}` : ROUTES.login;
}

/**
 * A redirect target that stays inside this app: a path, never another origin
 * ("//evil.example" or "https://…") and never the login page itself.
 */
export function safeRedirect(raw: string | null): string | null {
  if (!raw || !raw.startsWith('/') || raw.startsWith('//') || raw.startsWith(ROUTES.login)) return null;
  return raw;
}

/** Ends a session whose token has expired - once, with a message saying so. */
export function endExpiredSession(): void {
  if (!useAuthStore.getState().token) return;
  const returnTo = currentPath();
  useAuthStore.getState().logout();
  toast.warning('Your session has expired.', {
    description: 'Log in again to continue where you left off.',
    action: { label: 'Log in', onClick: () => window.location.assign(loginPath({ redirect: returnTo })) },
  });
}
