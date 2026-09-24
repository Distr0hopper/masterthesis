import { ExternalLink, Star } from 'lucide-react';
import {
  type ComponentDisplayModel,
} from '@/api/components';
import { cn } from '@/lib/utils';
import { ROUTES } from '@/lib/routes';
import { NO_DATA_INPUTS_SCORE } from './lib/portKinds';
import { DRAG_MIME, type ComponentDragPayload } from './types';
import { DomainBadges } from '@/components/common/DomainBadges';

interface ComponentPaletteCardProps {
  /** `component.match` is the backend's ranking of this candidate against the canvas */
  component: ComponentDisplayModel;
}

/**
 * One draggable component in the {@link WorkflowSidebar} palette. The whole card is the
 * drag source; dropping it on the canvas costs no request because the payload carries
 * every field a node needs (see {@link ComponentDragPayload}).
 */
export function ComponentPaletteCard({ component }: ComponentPaletteCardProps) {
  const { match } = component;

  return (
    <div
      draggable
      onDragStart={(e) => {
        const payload: ComponentDragPayload = {
          componentId: component.id,
          componentName: component.name,
          domains: component.domains,
          parameters: component.parameters,
        };
        e.dataTransfer.setData(DRAG_MIME, JSON.stringify(payload));
        e.dataTransfer.effectAllowed = 'copy';
      }}
      className={cn(
        'flex cursor-grab flex-col gap-2 rounded-md border border-slate-200 bg-white p-3 transition-colors hover:border-jmu-blue-300 active:cursor-grabbing',
        // no data inputs at all - still draggable, just de-emphasised
        match?.score === NO_DATA_INPUTS_SCORE && 'opacity-60',
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

      {match?.componentName && match.status === 'compatible' && (
        <span className="flex items-center gap-1 text-xs text-green-600">
          <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-green-500" />
          <span className="truncate">Compatible with {match.componentName}</span>
        </span>
      )}
      {match?.componentName && match.status === 'unverified' && (
        <span
          className="flex items-center gap-1 text-xs text-amber-600"
          title="The file types fit, but the formats could not be verified"
        >
          <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" />
          <span className="truncate">Possibly compatible with {match.componentName}</span>
        </span>
      )}

      <DomainBadges domains={component.domains} />
    </div>
  );
}