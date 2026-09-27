import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/store/auth.store.ts';
import { loginPath } from '@/api/auth/session';

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated());
  const location = useLocation();
  // remember the page, so logging in (again) lands back on it
  if (!isAuthenticated) return <Navigate to={loginPath({ redirect: location.pathname + location.search })} replace />;
  return <>{children}</>;
}
