import type { ReactNode } from 'react';
import { Label } from '@/components/ui/label.tsx';

interface FormFieldProps {
  /** ties the label to the control - omit for controls that render their own label */
  htmlFor?: string;
  label: string;
  optional?: boolean;
  error?: string;
  children: ReactNode;
}

/**
 * Label + control + validation message, the layout every upload form field uses.
 * Shared so the component and workflow upload forms stay visually identical rather
 * than each re-spelling the same markup.
 */
export function FormField({ htmlFor, label, optional = false, error, children }: FormFieldProps) {
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={htmlFor}>
        {label}
        {optional && <span className="font-normal text-slate-500"> (optional)</span>}
      </Label>
      {children}
      {error && <p className="text-sm text-error-foreground">{error}</p>}
    </div>
  );
}
