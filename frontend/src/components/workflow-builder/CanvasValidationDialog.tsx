import { AlertTriangle, X } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog.tsx';
import { isBlocking, type ValidationError } from './lib/canvasValidation';

interface CanvasValidationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  errors: ValidationError[];
  onProceed: () => void;
}

export function CanvasValidationDialog({
  open,
  onOpenChange,
  errors,
  onProceed,
}: CanvasValidationDialogProps) {
  const blocking = errors.filter(isBlocking);
  const warnings = errors.filter((error) => !isBlocking(error));
  const canProceed = blocking.length === 0;

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>
            {canProceed ? 'Export this workflow?' : 'Cannot export workflow'}
          </AlertDialogTitle>
          <AlertDialogDescription>
            {canProceed
              ? 'The workflow is valid, but check the following before you export:'
              : 'Fix the following issues before you export:'}
          </AlertDialogDescription>
        </AlertDialogHeader>

        <ul className="max-h-64 space-y-2 overflow-y-auto text-sm text-slate-700">
          {blocking.map((error, index) => (
            <li key={`blocking-${index}`} className="flex items-start gap-2">
              <X className="mt-0.5 h-4 w-4 shrink-0 text-destructive" aria-hidden />
              <span>{error.message}</span>
            </li>
          ))}
          {warnings.map((error, index) => (
            <li key={`warning-${index}`} className="flex items-start gap-2">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" aria-hidden />
              <span>{error.message}</span>
            </li>
          ))}
        </ul>

        <AlertDialogFooter>
          {canProceed ? (
            <>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={onProceed}>Export anyway</AlertDialogAction>
            </>
          ) : (
            <AlertDialogAction>Close</AlertDialogAction>
          )}
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
