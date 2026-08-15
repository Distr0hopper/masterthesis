import { Link } from 'react-router-dom';
import { useMyWorkflows, WorkflowStatus } from '@/api/workflows';
import { WorkflowSection } from '@/components/workflow-mine/organisms/WorkflowSection';
import { ROUTES } from '@/lib/routes';

export default function MyWorkflowsPage() {
  const { data: workflows, isLoading } = useMyWorkflows();

  const displayModels = workflows ?? [];
  const published = displayModels.filter((w) => w.status === WorkflowStatus.VALIDATED);
  const unpublished = displayModels.filter((w) => w.status !== WorkflowStatus.VALIDATED);

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">My Workflows</h1>
      <p className="mt-1 text-slate-500">Workflows you've uploaded, including those still pending validation.</p>

      {isLoading ? (
        <p className="mt-8 text-slate-500">Loading workflows...</p>
      ) : displayModels.length === 0 ? (
        <p className="mt-8 text-slate-500">
          You haven't uploaded any workflows yet.{' '}
          <Link to={ROUTES.workflowUpload} className="font-semibold text-jmu-blue-800 hover:underline">
            Upload one
          </Link>
          .
        </p>
      ) : (
        <>
          <WorkflowSection title="Unpublished Workflows" workflows={unpublished} />
          <WorkflowSection title="Published Workflows" workflows={published} />
        </>
      )}
    </div>
  );
}
