import { Link, useSearchParams } from 'react-router-dom';
import { ComponentStatus, useMyComponents, type ComponentKind } from '@/api/components';
import { ComponentSection } from '@/components/component-mine/organisms/ComponentSection';
import { Pagination } from '@/components/common/Pagination';
import { Input } from '@/components/ui/input.tsx';
import { Label } from '@/components/ui/label.tsx';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useSplitPageParams } from '@/lib/useSplitPageParams';
import { KIND_ROUTES, ROUTES } from '@/lib/routes';
import { KIND_COPY } from '@/lib/componentKinds';
import { parseStatus, STATUS_GROUP_TITLES, STATUS_ORDER } from '@/lib/componentStatuses';

const ALL = 'all';
// a filter change starts every section over on its first page
const OFFSET_KEYS = ['publishedOffset', 'unpublishedOffset', 'deprecatedOffset'];

interface MyComponentsPageProps {
  kind: ComponentKind;
}

/** The caller's own components of one kind - My Tools or My Workflows. */
export default function MyComponentsPage({ kind }: MyComponentsPageProps) {
  const copy = KIND_COPY[kind];
  const routes = KIND_ROUTES[kind];
  const { limit, published, unpublished, deprecated } = useSplitPageParams();
  const [searchParams, setSearchParams] = useSearchParams();

  const statusFilter = parseStatus(searchParams.get('status'));
  const searchTerm = searchParams.get('search') ?? '';
  const isFiltered = !!statusFilter || !!searchTerm;

  const setFilter = (key: string, value: string) => {
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      if (value) params.set(key, value);
      else params.delete(key);
      OFFSET_KEYS.forEach((offsetKey) => params.delete(offsetKey));
      return params;
    });
  };

  const { data, isLoading } = useMyComponents({
    kind,
    limit,
    publishedOffset: published.offset,
    unpublishedOffset: unpublished.offset,
    deprecatedOffset: deprecated.offset,
    search: searchTerm || undefined,
  });

  const sections = [
    { status: ComponentStatus.DRAFT, page: data?.unpublished, params: unpublished },
    { status: ComponentStatus.PUBLISHED, page: data?.published, params: published },
    { status: ComponentStatus.DEPRECATED, page: data?.deprecated, params: deprecated },
  ].filter((section) => (!statusFilter || section.status === statusFilter) && (section.page?.total ?? 0) > 0);

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">My {copy.plural}</h1>
      <p className="mt-1 text-slate-500">{copy.mineSubtitle}</p>

      <Tabs value={statusFilter ?? ALL} onValueChange={(value) => setFilter('status', value === ALL ? '' : value)} className="mt-6">
        <TabsList>
          <TabsTrigger value={ALL}>All</TabsTrigger>
          {STATUS_ORDER.map((status) => (
            <TabsTrigger key={status} value={status}>
              {STATUS_GROUP_TITLES[status]}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <div className="mt-4 flex flex-col gap-2">
        <Label htmlFor="search">Search</Label>
        <Input
          id="search"
          placeholder="Search by name..."
          value={searchTerm}
          onChange={(e) => setFilter('search', e.target.value)}
        />
      </div>

      {isLoading ? (
        <p className="mt-8 text-slate-500">Loading {copy.pluralLower}...</p>
      ) : sections.length === 0 && isFiltered ? (
        <p className="mt-8 text-slate-500">No {copy.pluralLower} match your filters.</p>
      ) : sections.length === 0 ? (
        <p className="mt-8 text-slate-500">
          You don't have any {copy.pluralLower} yet.{' '}
          <Link to={routes.upload} className="font-semibold text-jmu-blue-800 hover:underline">
            Upload one
          </Link>
          {kind === 'workflow' && (
            <>
              {' '}
              or{' '}
              <Link to={ROUTES.builder} className="font-semibold text-jmu-blue-800 hover:underline">
                build one in the Workflow Builder
              </Link>
            </>
          )}
          .
        </p>
      ) : (
        sections.map(({ status, page, params }) => (
          <div key={status}>
            <ComponentSection
              title={`${STATUS_GROUP_TITLES[status]} ${copy.plural}`}
              components={page?.items ?? []}
              total={page?.total ?? 0}
              backTo={routes.mine}
            />
            <Pagination
              totalItems={page?.total ?? 0}
              itemsPerPage={limit}
              currentPage={params.page}
              onPageChange={params.goToPage}
            />
          </div>
        ))
      )}
    </div>
  );
}
