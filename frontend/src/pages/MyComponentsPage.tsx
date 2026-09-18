import { Link } from 'react-router-dom';
import { useMyComponents } from '@/api/components';
import { ComponentSection } from '@/components/component-mine/organisms/ComponentSection';
import { Pagination } from '@/components/common/Pagination';
import { useSplitPageParams } from '@/lib/useSplitPageParams';
import { ROUTES } from '@/lib/routes';

export default function MyComponentsPage() {
  const { limit, published, unpublished } = useSplitPageParams();

  const { data, isLoading } = useMyComponents({
    limit,
    publishedOffset: published.offset,
    unpublishedOffset: unpublished.offset,
  });

  const publishedTotal = data?.published.total ?? 0;
  const unpublishedTotal = data?.unpublished.total ?? 0;
  const isEmpty = publishedTotal === 0 && unpublishedTotal === 0;

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">My Components</h1>
      <p className="mt-1 text-slate-500">
        Components you've uploaded or packaged, including drafts that are still only visible to you.
      </p>

      {isLoading ? (
        <p className="mt-8 text-slate-500">Loading components...</p>
      ) : isEmpty ? (
        <p className="mt-8 text-slate-500">
          You haven't uploaded any components yet.{' '}
          <Link to={ROUTES.componentUpload} className="font-semibold text-jmu-blue-800 hover:underline">
            Upload one
          </Link>
          .
        </p>
      ) : (
        <>
          {unpublishedTotal > 0 && (
            <>
              <ComponentSection
                title="Unpublished Components"
                components={data?.unpublished.items ?? []}
                total={unpublishedTotal}
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
                title="Published Components"
                components={data?.published.items ?? []}
                total={publishedTotal}
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
