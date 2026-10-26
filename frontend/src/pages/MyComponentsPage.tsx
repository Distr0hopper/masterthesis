import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { ComponentStatus, useMyComponents } from '@/api/components';
import { ComponentSection } from '@/components/component-mine/organisms/ComponentSection';
import { Pagination } from '@/components/common/Pagination';
import { SourceFilter } from '@/components/common/SourceFilter';
import { StatusFilter } from '@/components/common/StatusFilter';
import { Input } from '@/components/ui/input.tsx';
import { Label } from '@/components/ui/label.tsx';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useSplitPageParams } from '@/lib/useSplitPageParams';
import { KIND_ROUTES, ROUTES } from '@/lib/routes';
import { KIND_COPY, KIND_ICONS, KINDS, parseKind } from '@/lib/componentKinds';
import { parseSource, sourcesFor } from '@/lib/componentSources';
import { parseStatus, STATUS_GROUP_TITLES } from '@/lib/componentStatuses';

const ALL = 'all';
// a filter change starts every section over on its first page
const OFFSET_KEYS = ['publishedOffset', 'unpublishedOffset', 'deprecatedOffset'];

const linkClass = 'font-semibold text-jmu-blue-800 hover:underline';

/** The caller's own components of both kinds - `?kind=` narrows it to Tools or Workflows. */
export default function MyComponentsPage() {
  const { limit, published, unpublished, deprecated } = useSplitPageParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();

  const kind = parseKind(searchParams.get('kind'));
  const statusFilter = parseStatus(searchParams.get('status'));
  const sources = sourcesFor(kind);
  // a source the chosen kind can't come from (e.g. packaged, on the Workflows tab) filters nothing
  const sourceFilter = parseSource(searchParams.get('source'));
  const activeSource = sourceFilter && sources.includes(sourceFilter) ? sourceFilter : undefined;
  const searchTerm = searchParams.get('search') ?? '';
  const isFiltered = !!statusFilter || !!activeSource || !!searchTerm;
  const itemLabel = kind ? KIND_COPY[kind].pluralLower : 'tools and workflows';
  const sectionNoun = kind ? KIND_COPY[kind].plural : 'Components';

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
    source: activeSource,
  });

  const sections = [
    { status: ComponentStatus.DRAFT, page: data?.unpublished, params: unpublished },
    { status: ComponentStatus.PUBLISHED, page: data?.published, params: published },
    { status: ComponentStatus.DEPRECATED, page: data?.deprecated, params: deprecated },
  ].filter((section) => (!statusFilter || section.status === statusFilter) && (section.page?.total ?? 0) > 0);

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">My Components</h1>
      <p className="mt-1 text-slate-500">
        Tools and workflows you've uploaded, packaged or built in the Workflow Builder, including drafts that are still
        only visible to you.
      </p>

      {/* a filter, not tabbed content - the sections below follow the URL's ?kind= */}
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

      <div className="mt-6 flex flex-col gap-4 sm:flex-row sm:items-end">
        <div className="flex flex-1 flex-col gap-2">
          <Label htmlFor="search">Search</Label>
          <Input
            id="search"
            placeholder="Search by name..."
            value={searchTerm}
            onChange={(e) => setFilter('search', e.target.value)}
          />
        </div>

        <div className="flex flex-col gap-2 sm:w-56">
          <Label htmlFor="source">Source</Label>
          <SourceFilter
            id="source"
            value={activeSource}
            sources={sources}
            onValueChange={(value) => setFilter('source', value ?? '')}
          />
        </div>

        <div className="flex flex-col gap-2 sm:w-56">
          <Label htmlFor="status">Status</Label>
          <StatusFilter id="status" value={statusFilter} onValueChange={(value) => setFilter('status', value ?? '')} />
        </div>
      </div>

      {isLoading ? (
        <p className="mt-8 text-slate-500">Loading {itemLabel}...</p>
      ) : sections.length === 0 && isFiltered ? (
        <p className="mt-8 text-slate-500">No {itemLabel} match your filters.</p>
      ) : sections.length === 0 ? (
        <p className="mt-8 text-slate-500">
          You don't have any {itemLabel} yet.{' '}
          {kind === 'tool' && (
            <Link to={KIND_ROUTES.tool.upload} className={linkClass}>
              Upload one
            </Link>
          )}
          {kind === 'workflow' && (
            <>
              <Link to={KIND_ROUTES.workflow.upload} className={linkClass}>
                Upload one
              </Link>{' '}
              or{' '}
              <Link to={ROUTES.builder} className={linkClass}>
                build one in the Workflow Builder
              </Link>
            </>
          )}
          {!kind && (
            <>
              <Link to={KIND_ROUTES.tool.upload} className={linkClass}>
                Upload a tool
              </Link>
              ,{' '}
              <Link to={KIND_ROUTES.workflow.upload} className={linkClass}>
                upload a workflow
              </Link>{' '}
              or{' '}
              <Link to={ROUTES.builder} className={linkClass}>
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
              title={`${STATUS_GROUP_TITLES[status]} ${sectionNoun}`}
              components={page?.items ?? []}
              total={page?.total ?? 0}
              // the current URL, filters included, so the detail page leads back to this exact view
              backTo={`${location.pathname}${location.search}`}
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
