import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ChevronDown, LogOut, Package, Search, Upload, User, Workflow, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useAuthStore } from '@/store/auth.store';
import { ROUTES } from '@/lib/routes';
import { GlobalSearch } from './GlobalSearch';

const navLinkClass = (active: boolean) =>
  cn(
    'whitespace-nowrap text-sm font-medium transition-colors',
    active ? 'text-white' : 'text-jmu-blue-200 hover:text-white',
  );

export default function Header() {
  const navigate = useNavigate();
  const location = useLocation();
  const { pathname } = location;
  // below xl there's no room for the field in the bar - a button opens it underneath instead
  const [searchOpen, setSearchOpen] = useState(false);
  useEffect(() => setSearchOpen(false), [location.key]);
  const user = useAuthStore((state) => state.user);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated());
  const logout = useAuthStore((state) => state.logout);

  const handleLogout = () => {
    logout();
    navigate(ROUTES.login);
  };

  const displayName = user?.firstName ?? user?.email.split('@')[0] ?? 'user';

  return (
    <header className="fixed inset-x-0 top-0 z-50 h-14 border-b border-jmu-blue-800 bg-jmu-blue-600 text-white">
      {/* logo, nav and actions keep their size and never wrap; the search in between is the
          one flexible part - it takes the free space up to a cap and gives it back first */}
      <div className="mx-auto flex h-full max-w-6xl items-center gap-6 px-4">
        <Link to={ROUTES.home} className="flex shrink-0 items-center gap-2.5">
          <img src="/icons/Icon-XS.svg" alt="" />
          <span className="whitespace-nowrap text-sm font-semibold uppercase tracking-tight">
            JMU Component Repository
          </span>
        </Link>

        <nav className="flex shrink-0 items-center gap-6">
          <Link to={ROUTES.home} className={navLinkClass(pathname === ROUTES.home)}>
            Home
          </Link>
          <Link
            to={ROUTES.components}
            className={navLinkClass(pathname === ROUTES.components || pathname.startsWith(`${ROUTES.components}/`))}
          >
            Components
          </Link>
          <Link
            to={ROUTES.workflows}
            className={navLinkClass(pathname === ROUTES.workflows || pathname.startsWith(`${ROUTES.workflows}/`))}
          >
            Workflows
          </Link>
          <Link
            to={ROUTES.builder}
            className={navLinkClass(pathname === ROUTES.builder || pathname.startsWith(`${ROUTES.builder}/`))}
          >
            Workflow Builder
          </Link>
        </nav>

        <div className="hidden min-w-0 flex-1 justify-end xl:flex">
          <GlobalSearch enableShortcut className="w-full min-w-32 max-w-72" />
        </div>

        <div className="ml-auto flex shrink-0 items-center gap-2 xl:ml-0">
          <button
            type="button"
            onClick={() => setSearchOpen((open) => !open)}
            className="rounded p-1.5 text-jmu-blue-100 transition-colors hover:text-white xl:hidden"
            aria-label={searchOpen ? 'Close search' : 'Search components and workflows'}
            aria-expanded={searchOpen}
          >
            {searchOpen ? <X size={16} /> : <Search size={16} />}
          </button>
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
                    <Link to={ROUTES.componentUpload} className="cursor-pointer text-slate-900">
                      <Package size={14} className="text-slate-500" />
                      Upload Component
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link to={ROUTES.workflowUpload} className="cursor-pointer text-slate-900">
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
                    <Link to={ROUTES.profile} className="cursor-pointer text-slate-900">
                      <User size={14} className="text-slate-500" />
                      Profile
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link to={ROUTES.myComponents} className="cursor-pointer text-slate-900">
                      <Package size={14} className="text-slate-500" />
                      My Components
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link to={ROUTES.myWorkflows} className="cursor-pointer text-slate-900">
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
              to={ROUTES.login}
              className="rounded-md bg-white px-3 py-1.5 text-sm font-medium text-jmu-blue-600 transition-colors hover:bg-jmu-blue-50"
            >
              Login
            </Link>
          )}
        </div>
      </div>

      {searchOpen && (
        <div className="border-b border-jmu-blue-800 bg-jmu-blue-600 px-4 py-2 xl:hidden">
          <GlobalSearch autoFocus onClose={() => setSearchOpen(false)} className="mx-auto max-w-6xl" />
        </div>
      )}
    </header>
  );
}