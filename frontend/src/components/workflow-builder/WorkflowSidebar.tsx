import { useMemo, useState } from 'react';
import { useComponents, useDomains } from '@/api/components';
import { useAuthStore } from '@/store/auth.store';
import { compareByRank, matchComponent, type OutputFrame } from './lib/typeChecking';
import { ComponentPaletteCard } from './ComponentPaletteCard.tsx';
import { WorkflowSidebarFilters } from './WorkflowSidebarFilters.tsx';

interface WorkflowSidebarProps {
  /** available outputs on the canvas, most-recent first - drives the ranking */
  outputStack: OutputFrame[];
}

export function WorkflowSidebar({ outputStack }: WorkflowSidebarProps) {
  const [search, setSearch] = useState('');
  const [selectedDomains, setSelectedDomains] = useState<string[]>([]);
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
    domain: selectedDomains,
    limit: 50,
    includeParameters: true,
    // the endpoint 401s on favoritesOnly for anonymous visitors, so the flag is gated on
    // auth as well as on the toggle - same guard ComponentsPage uses
    favoritesOnly: isAuthenticated && favoritesOnly,
  });
  const { data: domains } = useDomains();

  // drives the empty-state wording: "nothing here" reads as broken when the user has
  // actually filtered everything out
  const hasActiveFilter = Boolean(term) || selectedDomains.length > 0 || favoritesOnly;

  const ranked = useMemo(() => {
    const components = data?.items ?? [];
    return components
      .map((component) => ({ component, match: matchComponent(component.parameters, outputStack) }))
      .sort(compareByRank);
  }, [data, outputStack]);

  return (
    <aside className="flex w-[280px] shrink-0 flex-col border-r border-slate-200 bg-white">
      <WorkflowSidebarFilters
        search={search}
        selectedDomains={selectedDomains}
        favoritesOnly={favoritesOnly}
        domains={domains ?? []}
        onSearchChange={setSearch}
        onDomainsChange={setSelectedDomains}
        onFavoritesOnlyChange={setFavoritesOnly}
        showFavoritesToggle={isAuthenticated}
      />

      <div className="flex flex-1 flex-col gap-2 overflow-y-auto p-4">
        {isLoading ? (
          <p className="text-sm text-slate-500">Loading components...</p>
        ) : ranked.length === 0 ? (
          <p className="text-sm text-slate-500">
            {hasActiveFilter ? 'No components match these filters.' : 'No components found.'}
          </p>
        ) : (
          ranked.map(({ component, match }) => (
            <ComponentPaletteCard key={component.id} component={component} match={match} />
          ))
        )}
      </div>
    </aside>
  );
}
