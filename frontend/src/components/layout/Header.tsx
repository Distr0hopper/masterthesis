import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/store/auth.store';

export default function Header() {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated());
  const logout = useAuthStore((state) => state.logout);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <header className="bg-jmu-blue-600 text-white">
      <div className="container mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <Link to="/" className="text-lg font-semibold">
          JMU Component Repository
        </Link>

        <nav>
          <div className="flex items-center gap-6">
            <Link to="/" className="text-sm font-medium hover:underline">
              Home
            </Link>
            <Link to="/browse" className="text-sm font-medium hover:underline">
              Browse
            </Link>
            <Link to="/about" className="text-sm font-medium hover:underline">
              About
            </Link>
          </div>
        </nav>

        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <>
              <span className="text-sm">{user?.email}</span>
              <Button asChild variant="secondary" size="sm">
                <Link to="/upload">Upload</Link>
              </Button>
              <Button variant="outline" size="sm" onClick={handleLogout}>
                Logout
              </Button>
            </>
          ) : (
            <>
              <Link to="/login" className="text-sm font-medium hover:underline">
                Login
              </Link>
              <Link
                to="/register"
                className="rounded-md bg-white px-3 py-1.5 text-sm font-medium text-jmu-blue-600 transition-colors hover:bg-jmu-blue-50"
              >
                Register
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
