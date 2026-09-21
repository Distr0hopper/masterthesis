import { Link, useNavigate } from 'react-router-dom';
import { GitBranch, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button.tsx';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { useWorkflowDrafts } from '@/api/workflow-drafts';
import { DraftCardActions } from '@/components/workflow-builder/DraftCardActions';
import { formatRelativeTime } from '@/components/workflow-builder/lib/canvasState';
import { useAuthStore } from '@/store/auth.store';
import { ROUTES } from '@/lib/routes';

export default function WorkflowBuilderOverviewPage() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated());

  const { data: drafts, isLoading } = useWorkflowDrafts();

  const handleNew = () => navigate(ROUTES.builderNew);

  if (!isAuthenticated) {
    return (
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Workflows</h1>
        <div className="flex flex-col items-center gap-3 py-16 text-slate-400">
          <GitBranch className="h-10 w-10" />
          <p className="text-sm">Sign in to create and manage your workflows.</p>
          <Button asChild className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90">
            <Link to={ROUTES.login}>Sign in</Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Workflows</h1>
          <p className="mt-1 text-sm text-slate-500">
            Build and manage CWL workflow compositions
          </p>
        </div>

        <Button onClick={handleNew} className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90">
          <Plus size={14} />
          New Workflow
        </Button>
      </div>

      {isLoading ? (
        <p className="mt-8 text-slate-500">Loading workflows...</p>
      ) : (drafts ?? []).length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-16 text-slate-400">
          <GitBranch className="h-10 w-10" />
          <p className="text-sm">No saved workflows yet.</p>
          <Button onClick={handleNew} className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90">
            Create your first workflow
          </Button>
        </div>
      ) : (
        <div className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {(drafts ?? []).map((draft) => (
            <Card
              key={draft.id}
              role="button"
              tabIndex={0}
              onClick={() => navigate(ROUTES.builderWorkflow(draft.id))}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  navigate(ROUTES.builderWorkflow(draft.id));
                }
              }}
              className="cursor-pointer transition-colors hover:border-jmu-blue-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <CardContent className="flex flex-col gap-3 pt-6">
                <h3 className="break-all font-mono text-lg font-semibold text-slate-900">
                  {draft.name}
                </h3>

                <p className="text-sm text-slate-500">
                  {draft.nodeCount} {draft.nodeCount === 1 ? 'component' : 'components'} &middot;{' '}
                  Saved {formatRelativeTime(draft.updatedAt)}
                </p>

                <div className="flex justify-end border-t pt-3">
                  <DraftCardActions draft={draft} />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
