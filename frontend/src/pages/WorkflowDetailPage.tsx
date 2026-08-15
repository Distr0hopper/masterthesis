import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { isAxiosError } from 'axios';
import { ChevronLeft } from 'lucide-react';
import { useWorkflow } from '@/api/workflows';
import { WorkflowHeader } from '@/components/workflow-detail/organisms/WorkflowHeader';
import { WorkflowSteps } from '@/components/workflow-detail/organisms/WorkflowSteps';

export default function WorkflowDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const backTo = (location.state as { from?: string } | null)?.from ?? '/workflows';
  const backLabel = backTo === '/my-workflows' ? 'Back to My Workflows' : 'Back to Workflows';
  const { data: model, isLoading, error } = useWorkflow(id ?? '');

  if (isLoading) {
    return <p className="text-slate-500">Loading workflow...</p>;
  }

  if (isAxiosError(error) && error.response?.status === 404) {
    return (
      <div>
        <p className="text-slate-500">Workflow not found.</p>
        <Link to={backTo} className="mt-4 inline-flex items-center gap-1 text-sm text-jmu-blue-800 hover:underline">
          <ChevronLeft className="h-4 w-4" /> {backLabel}
        </Link>
      </div>
    );
  }

  if (error || !model) {
    return <p className="text-slate-500">Something went wrong loading this workflow.</p>;
  }

  return (
    <div>
      <WorkflowHeader model={model} backTo={backTo} backLabel={backLabel} onDeleted={() => navigate(backTo)} />
      <WorkflowSteps model={model} />
    </div>
  );
}
