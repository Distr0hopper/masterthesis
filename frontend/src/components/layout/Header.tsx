import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ChevronDown, FolderOpen, LogOut, Menu, Search, Upload, User, X, type LucideIcon } from 'lucide-react';
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
import { KIND_ICONS } from '@/lib/componentKinds';
import { GlobalSearch } from './GlobalSearch';
import { loginPath } from '@/api/auth/session';

const navLinkClass = (active: boolean) =>
  cn(
    'whitespace-nowrap text-sm font-medium transition-colors',
    active ? 'text-white' : 'text-jmu-blue-200 hover:text-white',
  );

const mobileLinkClass = (active = false) =>
  cn(
    'flex items-center gap-2.5 rounded-md px-3 py-2.5 text-sm font-medium transition-colors',
    active ? 'bg-white/10 text-white' : 'text-jmu-blue-100 hover:bg-white/10 hover:text-white',
  );

function MobileSectionTitle({ children }: { children: string }) {
  return (
    <p className="px-3 pb-1 pt-3 text-[11px] font-semibold uppercase tracking-wide text-jmu-blue-200">{children}</p>
  );
}

export default function Header() {
  const navigate = useNavigate();
  const location = useLocation();
  const { pathname } = location;
  // below xl there's no room for the field in the bar - a button opens it underneath instead
  const [searchOpen, setSearchOpen] = useState(false);
  // below lg the nav, upload and account links don't fit either - they move into a menu
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => {
    setSearchOpen(false);
    setMenuOpen(false);
  }, [location.key]);
  const user = useAuthStore((state) => state.user);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated());
  const logout = useAuthStore((state) => state.logout);

  const handleLogout = () => {
    setMenuOpen(false);
    logout();
    navigate(ROUTES.login);
  };

  // the detail pages (/tools/:id, /workflows/:id) are reached from the browse list
  const browseActive =
    pathname === ROUTES.browse ||
    pathname.startsWith(ROUTES.toolDetail('')) ||
    pathname.startsWith(ROUTES.workflowDetail(''));
  const ToolIcon = KIND_ICONS.tool;
  const WorkflowIcon = KIND_ICONS.workflow;

  const displayName = user?.firstName ?? user?.email.split('@')[0] ?? 'user';
  const loginTo = loginPath({ redirect: pathname + location.search });

  const navItems = [
    { to: ROUTES.home, label: 'Home', active: pathname === ROUTES.home },
    { to: ROUTES.browse, label: 'Browse', active: browseActive },
    {
      to: ROUTES.builder,
      label: 'Workflow Builder',
      active: pathname === ROUTES.builder || pathname.startsWith(`${ROUTES.builder}/`),
    },
  ];
  const uploadItems: { to: string; label: string; icon: LucideIcon }[] = [
    { to: ROUTES.toolUpload, label: 'Upload Tool', icon: ToolIcon },
    { to: ROUTES.workflowUpload, label: 'Upload Workflow', icon: WorkflowIcon },
  ];

  return (
    <header className="fixed inset-x-0 top-0 z-50 h-14 border-b border-jmu-blue-800 bg-jmu-blue-600 text-white">
      {/* logo, nav and actions keep their size and never wrap; the search in between is the
          one flexible part - it takes the free space up to a cap and gives it back first */}
      <div className="mx-auto flex h-full max-w-6xl items-center gap-6 px-4">
        <Link to={ROUTES.home} className="flex min-w-0 items-center gap-2.5 lg:shrink-0">
          <img src="/icons/Icon-XS.svg" alt="" />
          <span className="truncate whitespace-nowrap text-sm font-semibold uppercase tracking-tight">
            JMU Component Repository
          </span>
        </Link>

        <nav className="hidden shrink-0 items-center gap-6 lg:flex">
          {navItems.map(({ to, label, active }) => (
            <Link key={to} to={to} className={navLinkClass(active)}>
              {label}
            </Link>
          ))}
        </nav>

        <div className="hidden min-w-0 flex-1 justify-end xl:flex">
          <GlobalSearch enableShortcut className="w-full min-w-32 max-w-72" />
        </div>

        <div className="ml-auto flex shrink-0 items-center gap-2 xl:ml-0">
          <button
            type="button"
            onClick={() => {
              setSearchOpen((open) => !open);
              setMenuOpen(false);
            }}
            className="rounded p-1.5 text-jmu-blue-100 transition-colors hover:text-white xl:hidden"
            aria-label={searchOpen ? 'Close search' : 'Search components and workflows'}
            aria-expanded={searchOpen}
          >
            {searchOpen ? <X size={16} /> : <Search size={16} />}
          </button>
          {/* shown signed out too - the upload routes are protected and send you to the
              login first, then back to the upload page */}
          <button
            type="button"
            onClick={() => {
              setMenuOpen((open) => !open);
              setSearchOpen(false);
            }}
            className="rounded p-1.5 text-jmu-blue-100 transition-colors hover:text-white lg:hidden"
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={menuOpen}
            aria-controls="mobile-menu"
          >
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          <DropdownMenu>
            <DropdownMenuTrigger className="hidden items-center gap-1.5 rounded-md bg-white px-3 py-1.5 text-sm font-medium text-jmu-blue-600 transition-colors hover:bg-jmu-blue-50 focus:outline-none lg:flex">
              <Upload size={14} />
              Upload
              <ChevronDown size={13} />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-48">
              {uploadItems.map(({ to, label, icon: Icon }) => (
                <DropdownMenuItem key={to} asChild>
                  <Link to={to} className="cursor-pointer text-slate-900">
                    <Icon size={14} className="text-slate-500" />
                    {label}
                  </Link>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
          {isAuthenticated ? (
            <DropdownMenu>
              <DropdownMenuTrigger className="hidden items-center gap-1.5 rounded px-2.5 py-1.5 text-sm text-jmu-blue-100 transition-colors hover:text-white focus:outline-none lg:flex">
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
                    <FolderOpen size={14} className="text-slate-500" />
                    My Components
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} className="cursor-pointer text-slate-900">
                  <LogOut size={14} className="text-slate-500" />
                  Logout
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Link
              // come back to this page after logging in
              to={loginTo}
              className="hidden rounded-md bg-white px-3 py-1.5 text-sm font-medium text-jmu-blue-600 transition-colors hover:bg-jmu-blue-50 lg:block"
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

      {menuOpen && (
        <nav
          id="mobile-menu"
          aria-label="Main"
          className="max-h-[calc(100dvh-3.5rem)] overflow-y-auto border-b border-jmu-blue-800 bg-jmu-blue-600 px-4 pb-4 pt-2 shadow-lg lg:hidden"
        >
          <div className="mx-auto flex max-w-6xl flex-col">
            {navItems.map(({ to, label, active }) => (
              <Link key={to} to={to} className={mobileLinkClass(active)} aria-current={active ? 'page' : undefined}>
                {label}
              </Link>
            ))}

            <MobileSectionTitle>Upload</MobileSectionTitle>
            {uploadItems.map(({ to, label, icon: Icon }) => (
              <Link key={to} to={to} className={mobileLinkClass(pathname === to)}>
                <Icon size={16} />
                {label}
              </Link>
            ))}

            <div className="mt-3 border-t border-white/15 pt-1">
              {isAuthenticated ? (
                <>
                  <MobileSectionTitle>{`Signed in as ${displayName}`}</MobileSectionTitle>
                  <Link to={ROUTES.profile} className={mobileLinkClass(pathname === ROUTES.profile)}>
                    <User size={16} />
                    Profile
                  </Link>
                  <Link to={ROUTES.myComponents} className={mobileLinkClass(pathname === ROUTES.myComponents)}>
                    <FolderOpen size={16} />
                    My Components
                  </Link>
                  <button type="button" onClick={handleLogout} className={cn(mobileLinkClass(), 'w-full text-left')}>
                    <LogOut size={16} />
                    Logout
                  </button>
                </>
              ) : (
                <Link
                  to={loginTo}
                  className="mt-3 block rounded-md bg-white px-3 py-2.5 text-center text-sm font-medium text-jmu-blue-600 transition-colors hover:bg-jmu-blue-50"
                >
                  Login
                </Link>
              )}
            </div>
          </div>
        </nav>
      )}
    </header>
  );
}