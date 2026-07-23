import {useAuthStore} from "@/store/auth.store.ts";
import {Navigate} from "react-router-dom";

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
    const isAuthenticated = useAuthStore((state) => state.isAuthenticated());
    if (!isAuthenticated) return <Navigate to="/login" replace />;
    return <>{children}</>;
}