import { Link } from 'react-router-dom';
import { useMyWorkflows, WorkflowStatus, workflowTransformer, type WorkflowDisplayModel } from '@/api/workflows';
import { WorkflowCard } from '@/components/workflow-browse/WorkflowCard';

function WorkflowSection({ title, workflows }: { title: string; workflows: WorkflowDisplayModel[] }) {
  if (workflows.length === 0) return null;

  return (
    <section className="mt-8">
      <h2 className="text-lg font-semibold text-slate-900">
        {title} <span className="font-normal text-slate-500">({workflows.length})</span>
      </h2>
      <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {workflows.map((workflow) => (
          <WorkflowCard key={workflow.id} workflow={workflow} backTo="/my-workflows" />
        ))}
      </div>
    </section>
  );
}

export default function MyWorkflowsPage() {
  const { data: workflows, isLoading } = useMyWorkflows();

  const displayModels = workflowTransformer.toListDisplayModels(workflows ?? []);
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
          <Link to="/workflows/upload" className="font-semibold text-jmu-blue-800 hover:underline">
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
