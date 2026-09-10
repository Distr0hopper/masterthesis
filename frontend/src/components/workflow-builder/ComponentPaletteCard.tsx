import { ExternalLink, Star } from 'lucide-react';
import { Badge } from '@/components/ui/badge.tsx';
import {
  getDomainBadgeStyle,
  useDomains,
  type ComponentDisplayModel,
} from '@/api/components';
import { cn } from '@/lib/utils';
import { ROUTES } from '@/lib/routes';
import { NO_DATA_INPUTS_SCORE, type CompatibilityMatch } from './lib/typeChecking';
import { DRAG_MIME, type ComponentDragPayload } from './types';

interface ComponentPaletteCardProps {
  component: ComponentDisplayModel;
  /** ranking result for this candidate against the current canvas */
  match: CompatibilityMatch;
}

/**
 * One draggable component in the {@link WorkflowSidebar} palette. The whole card is the
 * drag source; dropping it on the canvas costs no request because the payload carries
 * every field a node needs (see {@link ComponentDragPayload}).
 */
export function ComponentPaletteCard({ component, match }: ComponentPaletteCardProps) {
  // safe to call per card - useDomains() has a 1h staleTime, so every card reads the
  // same cached entry rather than triggering a request of its own
  const { data: domains } = useDomains();

  return (
    <div
      draggable
      onDragStart={(e) => {
        const payload: ComponentDragPayload = {
          componentId: component.id,
          componentName: component.name,
          domain: component.domain,
          parameters: component.parameters,
        };
        e.dataTransfer.setData(DRAG_MIME, JSON.stringify(payload));
        e.dataTransfer.effectAllowed = 'copy';
      }}
      className={cn(
        'flex cursor-grab flex-col gap-2 rounded-md border border-slate-200 bg-white p-3 transition-colors hover:border-jmu-blue-300 active:cursor-grabbing',
        // no data inputs at all - still draggable, just de-emphasised
        match.score === NO_DATA_INPUTS_SCORE && 'opacity-60',
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="break-all font-mono text-sm font-semibold text-slate-900">
          {component.name}
        </span>
        <div className="flex shrink-0 items-center gap-1">
          {/* makes the favourites-first ordering legible, rather than looking arbitrary */}
          {component.isFavorite && (
            <Star
              className="mt-0.5 h-3.5 w-3.5 fill-amber-400 text-amber-400"
              aria-label="Favorite"
            />
          )}
          <a
            href={ROUTES.componentDetail(component.id)}
            target="_blank"
            rel="noreferrer"
            // the card is the drag source; without this the browser would start
            // its own link drag from the anchor and clobber the JSON payload
            draggable={false}
            onClick={(e) => e.stopPropagation()}
            className="rounded p-0.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-jmu-blue-800"
            aria-label={`Open ${component.name} details in a new tab`}
            title="Open details in a new tab"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>
      </div>

      {match.frame && (
        <span className="flex items-center gap-1 text-xs text-green-600">
          <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-green-500" />
          <span className="truncate">Compatible with {match.frame.componentName}</span>
        </span>
      )}

      <Badge
        variant="outline"
        className="w-fit"
        style={domains ? getDomainBadgeStyle(component.domain, domains) : undefined}
      >
        {component.domainDisplay}
      </Badge>
    </div>
  );
}