import { useEffect, useRef, useState } from 'react';
import { useDomains, useInfiniteComponents } from '@/api/components';
import { useAuthStore } from '@/store/auth.store';
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
    search: term || undefined,
    domain: selectedDomains,
    limit: PAGE_SIZE,
    includeParameters: true,
    rankAgainst,
    // the endpoint 401s on favoritesOnly for anonymous visitors, so the flag is gated on
    // auth as well as on the toggle - same guard ComponentsPage uses
    favoritesOnly: isAuthenticated && favoritesOnly,
  });
  const { data: domains } = useDomains();

  // drives the empty-state wording: "nothing here" reads as broken when the user has
  // actually filtered everything out
  const hasActiveFilter = Boolean(term) || selectedDomains.length > 0 || favoritesOnly;

  const components = data?.items ?? [];

  // load the next page once the end of the list scrolls into view
  const scrollRef = useRef<HTMLDivElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel || !hasNextPage) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !isFetchingNextPage) void fetchNextPage();
      },
      // start loading a little before the bottom is actually reached
      { root: scrollRef.current, rootMargin: '200px' },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

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
            {hasActiveFilter ? 'No components match these filters.' : 'No components found.'}
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
