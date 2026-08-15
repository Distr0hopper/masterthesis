import { Link } from 'react-router-dom';
import { useMyComponents } from '@/api/components';
import { ComponentCard } from '@/components/component-browser/ComponentCard';
import { MyComponentCardActions } from '@/components/component-mine/organisms/MyComponentCardActions';
import { ROUTES } from '@/lib/routes';

export default function MyComponentsPage() {
  const { data: components, isLoading } = useMyComponents();

  const displayModels = components ?? [];

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">My Components</h1>
      <p className="mt-1 text-slate-500">Components you've uploaded or packaged.</p>

      {isLoading ? (
        <p className="mt-8 text-slate-500">Loading components...</p>
      ) : (
        <>
          <p className="mt-6 text-sm text-slate-500">{displayModels.length} results</p>

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
        </>
      )}
    </div>
  );
}
