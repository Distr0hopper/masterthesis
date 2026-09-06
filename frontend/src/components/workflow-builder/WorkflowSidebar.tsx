import { useMemo, useState } from 'react';
import { Star } from 'lucide-react';
import { Badge } from '@/components/ui/badge.tsx';
import { Input } from '@/components/ui/input.tsx';
import { getDomainBadgeStyle, useComponents, useDomains } from '@/api/components';
import { useAuthStore } from '@/store/auth.store';
import { cn } from '@/lib/utils';
import {
  NO_DATA_INPUTS_SCORE,
  compareByRank,
  matchComponent,
  type OutputFrame,
} from './lib/typeChecking';
import { DRAG_MIME, type ComponentDragPayload } from './types';

interface WorkflowSidebarProps {
  /** available outputs on the canvas, most-recent first - drives the ranking */
  outputStack: OutputFrame[];
}

export function WorkflowSidebar({ outputStack }: WorkflowSidebarProps) {
  const [search, setSearch] = useState('');
  const [favoritesOnly, setFavoritesOnly] = useState(false);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated());
  const term = search.trim();
  // 50 matches the backend's MAX_LIMIT - the palette has no pagination UI of its own,
  // so it asks for as many matches as the API allows in one page and relies on the
  // search box to narrow things down beyond that.
  // includeParameters: the ranking needs every candidate's ports, which the list
  // endpoint otherwise omits.
  const { data, isLoading } = useComponents({
    search: term || undefined,
    limit: 50,
    includeParameters: true,
    // the endpoint 401s on favoritesOnly for anonymous visitors, so the flag is gated on
    // auth as well as on the toggle - same guard ComponentsPage uses
    favoritesOnly: isAuthenticated && favoritesOnly,
  });
  const { data: domains } = useDomains();

  const ranked = useMemo(() => {
    const components = data?.items ?? [];
    return components
      .map((component) => ({ component, match: matchComponent(component.parameters, outputStack) }))
      .sort(compareByRank);
  }, [data, outputStack]);

  return (
    <aside className="flex w-[280px] shrink-0 flex-col border-r border-slate-200 bg-white">
      <div className="flex flex-col gap-3 border-b border-slate-200 p-4">
        <span className="text-xs uppercase tracking-wide text-slate-500">Components</span>
        <Input
          placeholder="Search by name..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        {isAuthenticated && (
          <label
            htmlFor="builderFavoritesOnly"
            className="flex items-center gap-2 text-sm text-slate-700"
          >
            <input
              id="builderFavoritesOnly"
              type="checkbox"
              checked={favoritesOnly}
              onChange={(e) => setFavoritesOnly(e.target.checked)}
              className="h-4 w-4 rounded border-input accent-jmu-blue-800"
            />
            Favorites only
          </label>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-2 overflow-y-auto p-4">
        {isLoading ? (
          <p className="text-sm text-slate-500">Loading components...</p>
        ) : ranked.length === 0 ? (
          <p className="text-sm text-slate-500">
            {favoritesOnly ? 'No favorite components found.' : 'No components found.'}
          </p>
        ) : (
          ranked.map(({ component, match }) => (
            <div
              key={component.id}
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
                {/* makes the favourites-first ordering legible, rather than looking arbitrary */}
                {component.isFavorite && (
                  <Star
                    className="mt-0.5 h-3.5 w-3.5 shrink-0 fill-amber-400 text-amber-400"
                    aria-label="Favorite"
                  />
                )}
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
          ))
        )}
      </div>
    </aside>
  );
}
