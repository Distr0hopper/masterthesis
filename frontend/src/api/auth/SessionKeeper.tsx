import { useEffect } from 'react';
import { useAuthStore } from '@/store/auth.store';
import { isTokenExpired } from '@/lib/jwt';
import { endExpiredSession, refreshSessionIfDue } from './session';

/** how often an open tab re-checks whether its session has run out */
const EXPIRY_CHECK_MS = 60_000;

/**
 * Keeps the login state honest while the app is open: an expired token ends the session
 * the moment it expires (not when the next protected page 401s), and coming back to the
 * tab renews a due token. Renders nothing.
 */
export function SessionKeeper() {
  useEffect(() => {
    const checkExpiry = () => {
      const token = useAuthStore.getState().token;
      if (token && isTokenExpired(token)) endExpiredSession();
    };
    const onReturn = () => {
      if (document.visibilityState !== 'visible') return;
      checkExpiry();
      refreshSessionIfDue();
    };

    checkExpiry();
    document.addEventListener('visibilitychange', onReturn);
    window.addEventListener('focus', onReturn);
    // expiry only - this never renews, so an idle open tab still ends after a lifetime
    const timer = window.setInterval(checkExpiry, EXPIRY_CHECK_MS);
    return () => {
      document.removeEventListener('visibilitychange', onReturn);
      window.removeEventListener('focus', onReturn);
      window.clearInterval(timer);
    };
  }, []);

  return null;
}
