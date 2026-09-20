import type { ReactNode } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface DefinitionDisclosureProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** noun completing "Show ..." / "Hide ..." */
  label?: string;
  /** rendered only while open, so callers can defer loading it until then */
  children: ReactNode;
}

export function DefinitionDisclosure({
  open,
  onOpenChange,
  label = 'definition',
  children,
}: DefinitionDisclosureProps) {
  return (
    <>
      <button
        type="button"
        onClick={() => onOpenChange(!open)}
        className="flex w-fit items-center gap-1 text-sm text-slate-500 hover:text-slate-900"
      >
        {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        {open ? 'Hide' : 'Show'} {label}
      </button>
      {open && children}
    </>
  );
}
