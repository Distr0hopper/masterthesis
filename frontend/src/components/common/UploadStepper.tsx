import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface UploadStep {
  id: number;
  label: string;
}

interface UploadStepperProps {
  steps: UploadStep[];
  current: number;
  /** highest step reached so far - earlier steps stay clickable, later ones don't */
  furthest: number;
  onSelect: (step: number) => void;
}

export function UploadStepper({ steps, current, furthest, onSelect }: UploadStepperProps) {
  return (
    <ol className="mt-6 flex flex-wrap items-center gap-2">
      {steps.map((step, index) => {
        const isDone = step.id < current;
        const isActive = step.id === current;
        const canVisit = step.id <= furthest;
        return (
          <li key={step.id} className="flex items-center gap-2">
            <button
              type="button"
              disabled={!canVisit}
              onClick={() => onSelect(step.id)}
              className={cn(
                'flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors',
                isActive && 'bg-jmu-blue-800 text-white',
                !isActive && canVisit && 'text-slate-900 hover:bg-slate-100',
                !canVisit && 'cursor-not-allowed text-slate-400',
              )}
            >
              <span
                className={cn(
                  'flex h-5 w-5 items-center justify-center rounded-full border text-xs',
                  isActive && 'border-white',
                  isDone && 'border-jmu-blue-800 bg-jmu-blue-800 text-white',
                )}
              >
                {isDone ? <Check className="h-3 w-3" /> : step.id}
              </span>
              {step.label}
            </button>
            {index < steps.length - 1 && <span className="h-px w-6 bg-slate-300" aria-hidden />}
          </li>
        );
      })}
    </ol>
  );
}
