import { Link } from 'react-router-dom';
import { useMyComponents, type ComponentKind } from '@/api/components';
import { ComponentSection } from '@/components/component-mine/organisms/ComponentSection';
import { Pagination } from '@/components/common/Pagination';
import { useSplitPageParams } from '@/lib/useSplitPageParams';
import { KIND_ROUTES, ROUTES } from '@/lib/routes';
import { KIND_COPY } from '@/lib/componentKinds';

interface MyComponentsPageProps {
  kind: ComponentKind;
}

/** The caller's own components of one kind - My Tools or My Workflows. */
export default function MyComponentsPage({ kind }: MyComponentsPageProps) {
  const copy = KIND_COPY[kind];
  const routes = KIND_ROUTES[kind];
  const { limit, published, unpublished } = useSplitPageParams();

  const { data, isLoading } = useMyComponents({
    kind,
    limit,
    publishedOffset: published.offset,
    unpublishedOffset: unpublished.offset,
  });

  const publishedTotal = data?.published.total ?? 0;
  const unpublishedTotal = data?.unpublished.total ?? 0;
  const isEmpty = publishedTotal === 0 && unpublishedTotal === 0;

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">My {copy.plural}</h1>
      <p className="mt-1 text-slate-500">{copy.mineSubtitle}</p>

      {isLoading ? (
        <p className="mt-8 text-slate-500">Loading {copy.pluralLower}...</p>
      ) : isEmpty ? (
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
        <>
          {unpublishedTotal > 0 && (
            <>
              <ComponentSection
                title={`Unpublished ${copy.plural}`}
                components={data?.unpublished.items ?? []}
                total={unpublishedTotal}
                backTo={routes.mine}
              />
              <Pagination
                totalItems={unpublishedTotal}
                itemsPerPage={limit}
                currentPage={unpublished.page}
                onPageChange={unpublished.goToPage}
              />
            </>
          )}

          {publishedTotal > 0 && (
            <>
              <ComponentSection
                title={`Published ${copy.plural}`}
                components={data?.published.items ?? []}
                total={publishedTotal}
                backTo={routes.mine}
              />
              <Pagination
                totalItems={publishedTotal}
                itemsPerPage={limit}
                currentPage={published.page}
                onPageChange={published.goToPage}
              />
            </>
          )}
        </>
      )}
    </div>
  );
}
