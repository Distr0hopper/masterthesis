import { ExternalLink } from 'lucide-react';
import type { ComponentKind } from '@/api/components';
import { ROUTES, componentDetailRoute } from '@/lib/routes';
import { cn } from '@/lib/utils';

interface ComponentLinkProps {
  componentId: string;
  /** when unknown, the link goes through /components/:id, which resolves the kind */
  kind?: ComponentKind;
  name: string;
  version?: number | null;
  className?: string;
}

/**
 * A component's name, linking to its detail page in a new tab - so a step's binding can
 * be checked without losing whatever page (upload wizard, workflow detail) it sits on.
 */
export function ComponentLink({ componentId, kind, name, version, className }: ComponentLinkProps) {
  return (
    <a
      href={kind ? componentDetailRoute(kind, componentId) : ROUTES.componentDetail(componentId)}
      target="_blank"
      rel="noreferrer"
      title="Open details in a new tab"
      aria-label={`Open ${name} details in a new tab`}
      className={cn('inline-flex items-baseline hover:underline', className)}
    >
      <span className="font-mono text-sm font-semibold text-slate-900">{name}</span>
      {version != null && <span className="text-xs text-slate-500">&nbsp;v{version}</span>}
      <ExternalLink className="ml-1.5 h-3.5 w-3.5 self-center text-slate-400" />
    </a>
  );
}
