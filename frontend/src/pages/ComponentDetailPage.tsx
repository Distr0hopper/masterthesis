import { Link, Navigate, useLocation, useNavigate, useParams } from 'react-router-dom';
import { isAxiosError } from 'axios';
import { ChevronLeft } from 'lucide-react';
import { useComponent, type ComponentKind } from '@/api/components';
import { ComponentHeader } from '@/components/component-detail/organisms/ComponentHeader';
import { RelatedComponents } from '@/components/component-detail/organisms/RelatedComponents';
import { UsedInWorkflows } from '@/components/component-detail/organisms/UsedInWorkflows';
import { ToolTabs } from '@/components/tool-detail/organisms/ToolTabs';
import { WorkflowDefinition } from '@/components/workflow-detail/organisms/WorkflowDefinition';
import { WorkflowSteps } from '@/components/workflow-detail/organisms/WorkflowSteps';
import { KIND_ROUTES, componentDetailRoute } from '@/lib/routes';
import { KIND_COPY } from '@/lib/componentKinds';

interface ComponentDetailPageProps {
  /** the kind the route is for - omitted on /components/:id, which only resolves and redirects */
  kind?: ComponentKind;
}

/**
 * The detail page of either kind: a shared header, then what only that kind has - a
 * tool's CWL/container/ports, a workflow's definition and steps - and, for both, the
 * workflows using it.
 */
export default function ComponentDetailPage({ kind }: ComponentDetailPageProps) {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { data: model, isLoading, error } = useComponent(id ?? '');

  // until it has loaded, the route's kind is the best guess for where "back" leads
  const routes = KIND_ROUTES[model?.kind ?? kind ?? 'tool'];
  const copy = KIND_COPY[model?.kind ?? kind ?? 'tool'];
  const backTo = (location.state as { from?: string } | null)?.from ?? routes.browse;
  const backLabel = backTo === routes.mine ? `Back to My ${copy.plural}` : `Back to ${copy.plural}`;

  if (isLoading) {
    return <p className="text-slate-500">Loading...</p>;
  }

  if (isAxiosError(error) && error.response?.status === 404) {
    return (
      <div>
        <p className="text-slate-500">{kind ? `${KIND_COPY[kind].singular} not found.` : 'Not found.'}</p>
        <Link to={backTo} className="mt-4 inline-flex items-center gap-1 text-sm text-jmu-blue-800 hover:underline">
          <ChevronLeft className="h-4 w-4" /> {backLabel}
        </Link>
      </div>
    );
  }

  if (error || !model) {
    return <p className="text-slate-500">Something went wrong loading this page.</p>;
  }

  // a /components/:id link, or a tool's id under /workflows - land on the right page
  if (model.kind !== kind) {
    return <Navigate to={componentDetailRoute(model.kind, model.id)} state={location.state} replace />;
  }

  return (
    <div>
      <ComponentHeader model={model} backTo={backTo} backLabel={backLabel} onDeleted={() => navigate(backTo)} />
      {model.kind === 'tool' ? (
        <ToolTabs model={model} />
      ) : (
        <>
          <WorkflowDefinition model={model} />
          <WorkflowSteps model={model} />
        </>
      )}
      <UsedInWorkflows componentId={model.id} version={model.version} />
      <RelatedComponents />
    </div>
  );
}
