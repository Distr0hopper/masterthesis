import type { ReactNode } from 'react';
import { AlertTriangle, Info, Loader2 } from 'lucide-react';

interface UploadSourceStepProps {
  /** where the upload comes from - a FileDropzone, or the GitHub repo-URL field */
  source: ReactNode;
  /** info box under the source - defaults to the ontology/EDAM explanation */
  hint?: ReactNode;
  /** problems found while reading the source that block continuing */
  issues?: string[];
  /** the source couldn't be read at all */
  error?: string;
  /** non-blocking information about what was read */
  notice?: ReactNode;
  isReading?: boolean;
  readingLabel?: string;
}

const ONTOLOGY_HINT = (
  <>
    Parameter formats are resolved against the ontology referenced in the CWL&apos;s{' '}
    <code className="text-xs">$schemas</code>. Currently only the <strong>EDAM</strong> ontology (
    <code className="text-xs">http://edamontology.org/</code>) is supported. The workflow builder can only verify that
    two components fit together when both declare an EDAM format - ports without a format, or with a format from another
    ontology, are kept but not labelled and show up as unverified connections.
  </>
);

/**
 * The opening step of every upload: only the source (a file, or a GitHub repo). Name,
 * domains and description follow once it's been read - they depend on what it contains.
 */
export function UploadSourceStep({
  source,
  hint = ONTOLOGY_HINT,
  issues = [],
  error,
  notice,
  isReading = false,
  readingLabel = 'Reading...',
}: UploadSourceStepProps) {
  return (
    <div className="flex flex-col gap-6">
      {source}

      {isReading && (
        <p className="flex items-center gap-2 text-sm text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          {readingLabel}
        </p>
      )}

      {error && <p className="rounded-md bg-error px-3 py-2 text-sm text-error-foreground">{error}</p>}

      {issues.map((issue) => (
        <div key={issue} className="flex items-start gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{issue}</span>
        </div>
      ))}

      {notice}

      <div className="flex items-start gap-2 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">
        <Info className="mt-0.5 h-4 w-4 shrink-0" />
        <span>{hint}</span>
      </div>
    </div>
  );
}
