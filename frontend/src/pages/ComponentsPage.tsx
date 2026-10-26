import { useSearchParams } from 'react-router-dom';
import { useComponents, useDomains } from '@/api/components';
import { ComponentCard } from '@/components/component-browse/ComponentCard';
import { ListFilters } from '@/components/common/ListFilters';
import { Pagination } from '@/components/common/Pagination';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAuthStore } from '@/store/auth.store';
import { usePageParams } from '@/lib/usePageParams';
import { KIND_COPY, KIND_ICONS, KINDS, parseKind } from '@/lib/componentKinds';

const ALL = 'all';

/** The public browse list of both kinds - `?kind=` narrows it to Tools or Workflows. */
export default function ComponentsPage() {
  const { limit, offset, setOffset, getFilter, setFilter, getFilterAll, setFilterAll } = usePageParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated());

  const kind = parseKind(getFilter('kind'));
  const itemLabel = kind ? KIND_COPY[kind].pluralLower : 'tools and workflows';
  const searchTerm = getFilter('search');
  const selectedDomains = getFilterAll('domain');
  const hideMine = searchParams.get('hideMine') === 'true';
  const favoritesOnly = searchParams.get('favoritesOnly') === 'true';

  const setBooleanFilter = (key: string, value: boolean) => {
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      if (value) params.set(key, 'true');
      else params.delete(key);
      params.set('offset', '0');
      return params;
    });
  };

  const { data: domains } = useDomains();
  const { data, isLoading } = useComponents({
    kind,
    domain: selectedDomains,
    excludeMine: isAuthenticated && hideMine,
    favoritesOnly: isAuthenticated && favoritesOnly,
    search: searchTerm || undefined,
    limit,
    offset,
  });

  const displayModels = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Browse</h1>
      <p className="mt-1 text-slate-500">Reusable CWL tools and the workflows composed of them.</p>

      {/* a filter, not tabbed content - the one list below follows the URL's ?kind= */}
      <Tabs
        value={kind ?? ALL}
        onValueChange={(value) => setFilter('kind', value === ALL ? '' : value)}
        className="mt-6"
      >
        <TabsList>
          <TabsTrigger value={ALL}>All</TabsTrigger>
          {KINDS.map((k) => {
            const Icon = KIND_ICONS[k];
            return (
              <TabsTrigger key={k} value={k} className="gap-1.5">
                <Icon className="h-4 w-4" />
                {KIND_COPY[k].plural}
              </TabsTrigger>
            );
          })}
        </TabsList>
      </Tabs>

      <ListFilters
        searchTerm={searchTerm}
        selectedDomains={selectedDomains}
        domains={domains ?? []}
        onSearchTermChange={(value) => setFilter('search', value)}
        onDomainsChange={(value) => setFilterAll('domain', value)}
        showUserToggles={isAuthenticated}
        favoritesOnly={favoritesOnly}
        onFavoritesOnlyChange={(value) => setBooleanFilter('favoritesOnly', value)}
        hideMine={hideMine}
        onHideMineChange={(value) => setBooleanFilter('hideMine', value)}
        itemLabel={itemLabel}
      />

      {isLoading ? (
        <p className="mt-8 text-slate-500">Loading {itemLabel}...</p>
      ) : (
        <>
          <p className="mt-6 text-sm text-slate-500">{total} results</p>

          {displayModels.length === 0 ? (
            <p className="mt-8 text-slate-500">No {itemLabel} found.</p>
          ) : (
            <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {displayModels.map((component) => (
                <ComponentCard key={component.id} component={component} />
              ))}
            </div>
          )}

          <Pagination
            totalItems={total}
            itemsPerPage={limit}
            currentPage={Math.floor(offset / limit) + 1}
            onPageChange={(page) => setOffset((page - 1) * limit)}
          />
        </>
      )}
    </div>
  );
}
