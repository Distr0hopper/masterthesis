import {useAuthStore} from "@/store/auth.store.ts";
import {Navigate} from "react-router-dom";
import {ROUTES} from "@/lib/routes";

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
    const isAuthenticated = useAuthStore((state) => state.isAuthenticated());
    if (!isAuthenticated) return <Navigate to={ROUTES.login} replace />;
    return <>{children}</>;
}