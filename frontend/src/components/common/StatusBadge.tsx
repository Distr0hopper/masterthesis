import { Badge } from '@/components/ui/badge.tsx';
import { ComponentStatus, STATUS_LABELS } from '@/api/components';
import { cn } from '@/lib/utils';

const STATUS_STYLE: Record<ComponentStatus, string> = {
  [ComponentStatus.PUBLISHED]: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  [ComponentStatus.DRAFT]: 'border-gray-300 bg-gray-100 text-gray-700',
  [ComponentStatus.DEPRECATED]: 'border-amber-200 bg-amber-50 text-amber-800',
};

const DOT_STYLE: Record<ComponentStatus, string> = {
  [ComponentStatus.PUBLISHED]: 'bg-emerald-500',
  [ComponentStatus.DRAFT]: 'bg-gray-400',
  [ComponentStatus.DEPRECATED]: 'bg-amber-500',
};

const STATUS_HINT: Record<ComponentStatus, string> = {
  [ComponentStatus.PUBLISHED]: 'Visible to everyone and offered in the Workflow Builder',
  [ComponentStatus.DRAFT]: 'Only visible to you',
  [ComponentStatus.DEPRECATED]: "Keeps working where it already runs, but can't be used in new workflows",
};

interface StatusBadgeProps {
  status: ComponentStatus;
  /** what it means, more specifically than the status's own hint (e.g. a deprecation note) */
  hint?: string | null;
  className?: string;
}

/** Where a version stands - the same colours and words wherever a status is shown. */
export function StatusBadge({ status, hint, className }: StatusBadgeProps) {
  return (
    <Badge
      variant="outline"
      className={cn('w-fit gap-1.5', STATUS_STYLE[status], className)}
      title={hint ?? STATUS_HINT[status]}
    >
      <span className={cn('h-1.5 w-1.5 shrink-0 rounded-full', DOT_STYLE[status])} aria-hidden />
      {STATUS_LABELS[status]}
    </Badge>
  );
}
