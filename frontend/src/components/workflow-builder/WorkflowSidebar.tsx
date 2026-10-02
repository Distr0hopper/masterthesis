import { useState } from 'react';
import { useDomains, useInfiniteComponents } from '@/api/components';
import { useAuthStore } from '@/store/auth.store';
import { useLoadMoreOnScroll } from '@/lib/useLoadMoreOnScroll';
import { ComponentPaletteCard } from './ComponentPaletteCard.tsx';
import { WorkflowSidebarFilters } from './WorkflowSidebarFilters.tsx';

interface WorkflowSidebarProps {
  /** the component of every canvas node, most recently added first - the backend ranks against these */
  rankAgainst: string[];
}

const PAGE_SIZE = 20;

export function WorkflowSidebar({ rankAgainst }: WorkflowSidebarProps) {
  const [search, setSearch] = useState('');
  const [selectedDomains, setSelectedDomains] = useState<string[]>([]);
  const [favoritesOnly, setFavoritesOnly] = useState(false);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated());
  const term = search.trim();
  // Loaded a page at a time as the list scrolls, so a large repository is never fetched in
  // one go. The backend ranks the whole filtered set against the canvas before paging, so
  // the pages arrive in their final order and each item carries its `match`.
  // includeParameters: a dropped card becomes a node, which needs the component's ports.
  const { data, isLoading, hasNextPage, isFetchingNextPage, fetchNextPage } = useInfiniteComponents({
    // tools only for now: the backend already exports and syncs a canvas nesting a
    // workflow, so offering workflows here is what enables nesting in the builder
    kind: 'tool',
    search: term || undefined,
    domain: selectedDomains,
    limit: PAGE_SIZE,
    includeParameters: true,
    rankAgainst,
    favoritesFirst: isAuthenticated,
    favoritesOnly: isAuthenticated && favoritesOnly,
  });
  const { data: domains } = useDomains();

  const hasActiveFilter = Boolean(term) || selectedDomains.length > 0 || favoritesOnly;

  const components = data?.items ?? [];

  const { scrollRef, sentinelRef } = useLoadMoreOnScroll({ hasNextPage, isFetchingNextPage, fetchNextPage });

  const loadedCount = components.length;

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

      <div ref={scrollRef} className="flex flex-1 flex-col gap-2 overflow-y-auto p-4">
        {isLoading ? (
          <p className="text-sm text-slate-500">Loading components...</p>
        ) : components.length === 0 ? (
          <p className="text-sm text-slate-500">
            {hasActiveFilter ? 'No tools match these filters.' : 'No tools found.'}
          </p>
        ) : (
          <>
            {components.map((component) => (
              <ComponentPaletteCard key={component.id} component={component} />
            ))}
            <div ref={sentinelRef} />
            <p className="pt-1 text-center text-xs text-slate-400">
              {isFetchingNextPage
                ? 'Loading more...'
                : `Showing ${loadedCount} of ${data?.total ?? loadedCount}${hasNextPage ? ' - scroll for more' : ''}`}
            </p>
          </>
        )}
      </div>
    </aside>
  );
}
