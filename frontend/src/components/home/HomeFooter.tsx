import { Link } from 'react-router-dom';
import { ROUTES } from '@/lib/routes';

export function HomeFooter() {
  return (
    <footer className="mt-10 flex flex-col gap-3 border-t pt-6 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
      <p>© 2026 Chair of Computer Science II, Julius-Maximilians-Universität Würzburg</p>
      <div className="flex gap-4">
        <Link to={ROUTES.about} className="hover:text-slate-900">
          About
        </Link>
        <Link to={ROUTES.tools} className="hover:text-slate-900">
          Tools
        </Link>
      </div>
    </footer>
  );
}
