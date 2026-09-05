import { Link } from 'react-router-dom';
import { useMyComponents } from '@/api/components';
import { ComponentCard } from '@/components/component-browser/ComponentCard';
import { MyComponentCardActions } from '@/components/component-mine/organisms/MyComponentCardActions';
import { Pagination } from '@/components/common/Pagination';
import { usePageParams } from '@/lib/usePageParams';
import { ROUTES } from '@/lib/routes';

export default function MyComponentsPage() {
  const { limit, offset, setOffset } = usePageParams();
  const { data, isLoading } = useMyComponents({ limit, offset });

  const displayModels = data?.items ?? [];
  const total = data?.total ?? 0;

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">My Components</h1>
      <p className="mt-1 text-slate-500">Components you've uploaded or packaged.</p>

      {isLoading ? (
        <p className="mt-8 text-slate-500">Loading components...</p>
      ) : (
        <>
          <p className="mt-6 text-sm text-slate-500">{total} results</p>

          {displayModels.length === 0 ? (
            <p className="mt-8 text-slate-500">
              You haven't uploaded any components yet.{' '}
              <Link to={ROUTES.componentUpload} className="font-semibold text-jmu-blue-800 hover:underline">
                Upload one
              </Link>
              .
            </p>
          ) : (
            <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {displayModels.map((component) => (
                <ComponentCard key={component.id} component={component} actions={<MyComponentCardActions component={component} />} />
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
