import { Link, useParams } from 'react-router-dom';
import { isAxiosError } from 'axios';
import { ChevronLeft } from 'lucide-react';
import { useComponent } from '@/api/components';
import { ComponentHeader } from '@/components/component-detail/organisms/ComponentHeader';
import { ComponentTabs } from '@/components/component-detail/organisms/ComponentTabs';
import { RelatedComponents } from '@/components/component-detail/organisms/RelatedComponents';
import { ROUTES } from '@/lib/routes';

export default function ComponentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: model, isLoading, error } = useComponent(id ?? '');

  if (isLoading) {
    return <p className="text-slate-500">Loading component...</p>;
  }

  if (isAxiosError(error) && error.response?.status === 404) {
    return (
      <div>
        <p className="text-slate-500">Component not found.</p>
        <Link to={ROUTES.browse} className="mt-4 inline-flex items-center gap-1 text-sm text-jmu-blue-800 hover:underline">
          <ChevronLeft className="h-4 w-4" /> Back to Browse
        </Link>
      </div>
    );
  }

  if (error || !model) {
    return <p className="text-slate-500">Something went wrong loading this component.</p>;
  }

  return (
    <div>
      <ComponentHeader model={model} />
      <ComponentTabs model={model} />
      <RelatedComponents />
    </div>
  );
}
