import { Badge } from '@/components/ui/badge.tsx';
import { KIND_LABELS, type ComponentKind } from '@/api/components';
import { KIND_ICONS } from '@/lib/componentKinds';
import { cn } from '@/lib/utils';

interface KindBadgeProps {
  kind: ComponentKind;
  className?: string;
}

/** Whether a component is a tool or a workflow - its icon and name, the same everywhere. */
export function KindBadge({ kind, className }: KindBadgeProps) {
  const Icon = KIND_ICONS[kind];
  return (
    <Badge variant="outline" className={cn('w-fit gap-1 text-slate-700', className)}>
      <Icon className="h-3.5 w-3.5" aria-hidden />
      {KIND_LABELS[kind]}
    </Badge>
  );
}
