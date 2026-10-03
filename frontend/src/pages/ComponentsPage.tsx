import { useSearchParams, Link } from 'react-router-dom';
import { Upload } from 'lucide-react';
import { useComponents, useDomains, type ComponentKind } from '@/api/components';
import { ComponentCard } from '@/components/component-browse/ComponentCard';
import { ListFilters } from '@/components/common/ListFilters';
import { Pagination } from '@/components/common/Pagination';
import { Button } from '@/components/ui/button.tsx';
import { useAuthStore } from '@/store/auth.store';
import { usePageParams } from '@/lib/usePageParams';
import { KIND_ROUTES } from '@/lib/routes';
import { KIND_COPY } from '@/lib/componentKinds';

interface ComponentsPageProps {
  kind: ComponentKind;
}

/** The public browse list of one kind - Tools or Workflows. */
export default function ComponentsPage({ kind }: ComponentsPageProps) {
  const copy = KIND_COPY[kind];
  const { limit, offset, setOffset, getFilter, setFilter, getFilterAll, setFilterAll } = usePageParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated());

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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">{copy.plural}</h1>
          <p className="mt-1 text-slate-500">{copy.browseSubtitle}</p>
        </div>

        {isAuthenticated && (
          <Button asChild className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90">
            <Link to={KIND_ROUTES[kind].upload}>
              <Upload size={14} />
              {copy.uploadLabel}
            </Link>
          </Button>
        )}
      </div>

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
        itemLabel={copy.pluralLower}
      />

      {isLoading ? (
        <p className="mt-8 text-slate-500">Loading {copy.pluralLower}...</p>
      ) : (
        <>
          <p className="mt-6 text-sm text-slate-500">{total} results</p>

          {displayModels.length === 0 ? (
            <p className="mt-8 text-slate-500">No {copy.pluralLower} found.</p>
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
