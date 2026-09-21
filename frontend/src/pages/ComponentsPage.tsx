import { useSearchParams, Link } from 'react-router-dom';
import { Upload } from 'lucide-react';
import { useComponents, useDomains } from '@/api/components';
import { ComponentCard } from '@/components/component-browser/ComponentCard';
import { ComponentFilters } from '@/components/component-browser/ComponentFilters';
import { Pagination } from '@/components/common/Pagination';
import { Button } from '@/components/ui/button.tsx';
import { useAuthStore } from '@/store/auth.store';
import { usePageParams } from '@/lib/usePageParams';
import { ROUTES } from '@/lib/routes';

export default function ComponentsPage() {
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
        <h1 className="text-2xl font-semibold text-slate-900">Browse Repository</h1>

        {isAuthenticated && (
          <Button asChild className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90">
            <Link to={ROUTES.componentUpload}>
              <Upload size={14} />
              Upload Component
            </Link>
          </Button>
        )}
      </div>

      <ComponentFilters
        searchTerm={searchTerm}
        selectedDomains={selectedDomains}
        domains={domains ?? []}
        onSearchTermChange={(value) => setFilter('search', value)}
        onDomainsChange={(value) => setFilterAll('domain', value)}
        showHideMineToggle={isAuthenticated}
        hideMine={hideMine}
        onHideMineChange={(value) => setBooleanFilter('hideMine', value)}
        showFavoritesToggle={isAuthenticated}
        favoritesOnly={favoritesOnly}
        onFavoritesOnlyChange={(value) => setBooleanFilter('favoritesOnly', value)}
      />

      {isLoading ? (
        <p className="mt-8 text-slate-500">Loading components...</p>
      ) : (
        <>
          <p className="mt-6 text-sm text-slate-500">{total} results</p>

          {displayModels.length === 0 ? (
            <p className="mt-8 text-slate-500">No components found.</p>
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
