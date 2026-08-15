import { Link } from 'react-router-dom';
import { useMyWorkflows, workflowTransformer } from '@/api/workflows';
import { WorkflowCard } from '@/components/workflow-browse/WorkflowCard';

export default function MyWorkflowsPage() {
  const { data: workflows, isLoading } = useMyWorkflows();

  const displayModels = workflowTransformer.toListDisplayModels(workflows ?? []);

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">My Workflows</h1>
      <p className="mt-1 text-slate-500">Workflows you've uploaded, including those still pending validation.</p>

      {isLoading ? (
        <p className="mt-8 text-slate-500">Loading workflows...</p>
      ) : (
        <>
          <p className="mt-6 text-sm text-slate-500">{displayModels.length} results</p>

          {displayModels.length === 0 ? (
            <p className="mt-8 text-slate-500">
              You haven't uploaded any workflows yet.{' '}
              <Link to="/workflows/upload" className="font-semibold text-jmu-blue-800 hover:underline">
                Upload one
              </Link>
              .
            </p>
          ) : (
            <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {displayModels.map((workflow) => (
                <WorkflowCard key={workflow.id} workflow={workflow} backTo="/my-workflows" />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
