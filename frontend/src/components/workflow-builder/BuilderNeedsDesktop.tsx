import { Link } from 'react-router-dom';
import { Monitor } from 'lucide-react';
import { Button } from '@/components/ui/button.tsx';
import { ROUTES } from '@/lib/routes';

/**
 * Stands in for the builder on phone-sized screens: the palette is dragged onto the canvas
 * with HTML5 drag and drop, which touch browsers don't fire, and the sidebar alone would
 * fill the screen.
 */
export function BuilderNeedsDesktop() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center text-slate-500">
      <Monitor className="h-10 w-10 text-slate-400" />
      <h1 className="text-lg font-semibold text-slate-900">The Workflow Builder needs a larger screen</h1>
      <p className="max-w-sm text-sm">
        Components are dragged onto a canvas, which doesn't work on a phone. Open this page on a desktop
        to build workflows.
      </p>
      <Button asChild variant="outline" className="mt-2">
        <Link to={ROUTES.builder}>Back to my workflows</Link>
      </Button>
    </div>
  );
}
