import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ChevronDown, LogOut, Package, Upload, User, Workflow } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useAuthStore } from '@/store/auth.store';

const navLinkClass = (active: boolean) =>
  cn(
    'text-sm font-medium transition-colors',
    active ? 'text-white' : 'text-jmu-blue-200 hover:text-white',
  );

export default function Header() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const user = useAuthStore((state) => state.user);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated());
  const logout = useAuthStore((state) => state.logout);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const displayName = user?.firstName ?? user?.email.split('@')[0] ?? 'user';

  return (
    <header className="fixed inset-x-0 top-0 z-50 h-14 border-b border-jmu-blue-800 bg-jmu-blue-600 text-white">
      <div className="mx-auto flex h-full max-w-6xl items-center justify-between px-4">
        <Link to="/" className="flex items-center gap-2.5">
          <img src="/icons/Icon-XS.svg" alt="" />
          <span className="text-sm font-semibold uppercase tracking-tight">
            JMU Component Repository
          </span>
        </Link>

        <nav className="flex items-center gap-6">
          <Link to="/" className={navLinkClass(pathname === '/')}>
            Home
          </Link>
          <Link to="/browse" className={navLinkClass(pathname === '/browse')}>
            Browse
          </Link>
          <Link to="/workflows" className={navLinkClass(pathname === '/workflows' || pathname.startsWith('/workflows/'))}>
            Workflows
          </Link>
          <Link to="/builder" className={navLinkClass(pathname === '/builder')}>
            Workflow Builder
          </Link>
          <Link to="/about" className={navLinkClass(pathname === '/about')}>
            About
          </Link>
        </nav>

        <div className="flex items-center gap-2">
          {isAuthenticated ? (
            <>
              <DropdownMenu>
                <DropdownMenuTrigger className="flex items-center gap-1.5 rounded-md bg-white px-3 py-1.5 text-sm font-medium text-jmu-blue-600 transition-colors hover:bg-jmu-blue-50 focus:outline-none">
                  <Upload size={14} />
                  Upload
                  <ChevronDown size={13} />
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-48">
                  <DropdownMenuItem asChild>
                    <Link to="/components/upload" className="cursor-pointer text-slate-900">
                      <Package size={14} className="text-slate-500" />
                      Upload Component
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link to="/workflows/upload" className="cursor-pointer text-slate-900">
                      <Workflow size={14} className="text-slate-500" />
                      Upload Workflow
                    </Link>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>

              <DropdownMenu>
                <DropdownMenuTrigger className="flex items-center gap-1.5 rounded px-2.5 py-1.5 text-sm text-jmu-blue-100 transition-colors hover:text-white focus:outline-none">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white/20">
                    <User size={13} className="text-white" />
                  </span>
                  <span>{displayName}</span>
                  <ChevronDown size={13} />
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  <DropdownMenuItem asChild>
                    <Link to="/profile" className="cursor-pointer text-slate-900">
                      <User size={14} className="text-slate-500" />
                      Profile
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link to="/my-components" className="cursor-pointer text-slate-900">
                      <Package size={14} className="text-slate-500" />
                      My Components
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link to="/my-workflows" className="cursor-pointer text-slate-900">
                      <Workflow size={14} className="text-slate-500" />
                      My Workflows
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleLogout} className="cursor-pointer text-slate-900">
                    <LogOut size={14} className="text-slate-500" />
                    Logout
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </>
          ) : (
            <Link
              to="/login"
              className="rounded-md bg-white px-3 py-1.5 text-sm font-medium text-jmu-blue-600 transition-colors hover:bg-jmu-blue-50"
            >
              Login
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}