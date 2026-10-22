import { AlertTriangle, Info, X } from 'lucide-react';

interface CanvasNoticesProps {
  missingLabels: string[];
  unreadable: boolean;
  dropped: boolean;
  onDismissDropped: () => void;
  notSynced: string | null;
}

/**
 * What is wrong with the canvas, shown above it for as long as it is true - derived from
 * the canvas state on every render rather than announced once, so it can't be missed,
 * shown twice, or outlive the problem: replacing the last deleted component clears it.
 */
export function CanvasNotices({ missingLabels, unreadable, dropped, onDismissDropped, notSynced }: CanvasNoticesProps) {
  if (missingLabels.length === 0 && !unreadable && !dropped && !notSynced) return null;
  const count = missingLabels.length;

  return (
    <div className="flex flex-col gap-2 border-b bg-white px-4 py-2">
      {unreadable && (
        <p role="alert" className="flex items-start gap-2 rounded-md bg-error px-3 py-2 text-sm text-error-foreground">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          This workflow&apos;s canvas could not be read.
        </p>
      )}

      {count > 0 && (
        <p role="alert" className="flex items-start gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <span>
            <span className="font-medium">
              {count === 1 ? '1 component on this canvas was' : `${count} components on this canvas were`} deleted from
              the repository:
            </span>{' '}
            {missingLabels.join(', ')}. Remove or replace {count === 1 ? 'it' : 'them'} before saving or exporting.
          </span>
        </p>
      )}

      {notSynced && (
        <p role="status" className="flex items-start gap-2 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-700">
          <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <span>
            <span className="font-medium">Saved, but not in My Components yet:</span> {notSynced}
          </span>
        </p>
      )}

      {dropped && (
        <p className="flex items-start gap-2 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-700">
          <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <span className="flex-1">Some components or connections could not be restored - they may have been removed.</span>
          <button
            type="button"
            onClick={onDismissDropped}
            className="text-slate-500 hover:text-slate-900"
            aria-label="Dismiss"
          >
            <X className="h-4 w-4" />
          </button>
        </p>
      )}
    </div>
  );
}
