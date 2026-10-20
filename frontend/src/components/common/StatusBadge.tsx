import { Badge } from '@/components/ui/badge.tsx';
import { ComponentStatus, STATUS_LABELS } from '@/api/components';
import { cn } from '@/lib/utils';

// green: live for everyone. Yellow: careful - still runs, but not for new use (no red - it is
// no error). Grey: not public, only yours. Neutral gray, not slate - slate's blue tint reads
// as a colour of its own
const STATUS_STYLE: Record<ComponentStatus, string> = {
  [ComponentStatus.PUBLISHED]: 'border-emerald-300 text-emerald-700',
  [ComponentStatus.DRAFT]: 'border-gray-300 text-gray-600',
  [ComponentStatus.DEPRECATED]: 'border-amber-300 text-amber-700',
};

const STATUS_HINT: Record<ComponentStatus, string> = {
  [ComponentStatus.PUBLISHED]: 'Visible to everyone and offered in the Workflow Builder',
  [ComponentStatus.DRAFT]: 'Only visible to you',
  [ComponentStatus.DEPRECATED]: "Keeps working where it already runs, but can't be used in new workflows",
};

interface StatusBadgeProps {
  status: ComponentStatus;
  /** what to call it - a display model's `statusDisplay` (e.g. "Unpublished"); else the plain status */
  label?: string;
  /** what it means - a display model's `statusHint`, or a more specific text; else the status's own */
  hint?: string | null;
  className?: string;
}

/** Where a version stands - the same colours and words wherever a status is shown. */
export function StatusBadge({ status, label, hint, className }: StatusBadgeProps) {
  return (
    <Badge variant="outline" className={cn('w-fit', STATUS_STYLE[status], className)} title={hint ?? STATUS_HINT[status]}>
      {label ?? STATUS_LABELS[status]}
    </Badge>
  );
}
