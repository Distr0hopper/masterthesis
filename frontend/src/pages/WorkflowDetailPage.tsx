import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { isAxiosError } from 'axios';
import { ChevronLeft, Download, Globe, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { getDomainBadgeStyle, useDomains } from '@/api/components';
import {
  StepMatchStatus,
  useDeleteWorkflow,
  usePublishWorkflow,
  useWorkflow,
  WorkflowStatus,
  workflowsService,
  workflowTransformer,
} from '@/api/workflows';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { Button } from '@/components/ui/button.tsx';
import { StepMatchCard } from '@/components/workflow-detail/StepMatchCard';
import { useAuthStore } from '@/store/auth.store';
import { getErrorMessage } from '@/lib/errors';

export default function WorkflowDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const backTo = (location.state as { from?: string } | null)?.from ?? '/workflows';
  const backLabel = backTo === '/my-workflows' ? 'Back to My Workflows' : 'Back to Workflows';
  const { data: workflow, isLoading, error } = useWorkflow(id ?? '');
  const { data: domains } = useDomains();
  const currentUser = useAuthStore((state) => state.user);
  const { mutate: deleteWorkflow, isPending: isDeleting } = useDeleteWorkflow();
  const { mutate: publishWorkflow, isPending: isPublishing } = usePublishWorkflow();

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

  if (error || !workflow) {
    return <p className="text-slate-500">Something went wrong loading this workflow.</p>;
  }

  const model = workflowTransformer.toDetailDisplayModel(workflow);
  const canDelete = currentUser?.id === model.createdById;
  const allStepsConfirmed = model.steps.every((step) => step.matchStatus === StepMatchStatus.CONFIRMED);
  const canPublish = canDelete && model.status === WorkflowStatus.PENDING_VALIDATION;

  const handleDelete = () => {
    if (!confirm(`Delete workflow "${model.name}"? This cannot be undone.`)) return;
    deleteWorkflow(model.id, {
      onSuccess: () => {
        toast.success('Workflow deleted');
        navigate(backTo);
      },
      onError: (deleteError) => toast.error(getErrorMessage(deleteError)),
    });
  };

  const handlePublish = () => {
    publishWorkflow(model.id, {
      onSuccess: () => toast.success('Workflow published'),
      onError: (publishError) => toast.error(getErrorMessage(publishError)),
    });
  };

  return (
    <div>
      <Link to={backTo} className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900">
        <ChevronLeft className="h-4 w-4" /> {backLabel}
      </Link>

      {model.status === WorkflowStatus.PENDING_VALIDATION && (
        <div className="mt-4 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          This workflow is pending validation and is only visible to you. Confirm every step below, then click
          Publish to make it public.
        </div>
      )}

      <Card className="mt-4">
        <CardContent className="flex flex-col gap-3 pt-6">
          <div className="flex items-center justify-between">
            <div className="flex flex-wrap items-center gap-2">
              {model.domains.map((domainId, index) => (
                <Badge
                  key={domainId}
                  variant="outline"
                  className="w-fit"
                  style={domains ? getDomainBadgeStyle(domainId, domains) : undefined}
                >
                  {model.domainsDisplay[index]}
                </Badge>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <Button asChild variant="outline" size="sm">
                <a href={workflowsService.getDownloadUrl(model.id)}>
                  <Download className="mr-1 h-4 w-4" /> Download
                </a>
              </Button>

              {canPublish && (
                <Button
                  size="sm"
                  className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
                  onClick={handlePublish}
                  disabled={isPublishing || !allStepsConfirmed}
                  title={allStepsConfirmed ? undefined : 'Confirm every step before publishing'}
                >
                  <Globe className="mr-1 h-4 w-4" /> Publish
                </Button>
              )}

              {canDelete && (
                <Button variant="destructive" size="sm" onClick={handleDelete} disabled={isDeleting}>
                  <Trash2 className="mr-1 h-4 w-4" /> Delete
                </Button>
              )}
            </div>
          </div>

          <h1 className="font-mono text-2xl font-bold text-slate-900">{model.name}</h1>

          {model.description && <p className="text-slate-600">{model.description}</p>}

          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t pt-3 text-sm text-slate-500">
            <span>{model.createdByDisplay}</span>
            <span>Created {model.createdAtDisplay}</span>
            <span>Updated {model.updatedAtDisplay}</span>
          </div>
        </CardContent>
      </Card>

      <h2 className="mt-8 text-lg font-semibold text-slate-900">Steps</h2>
      <div className="mt-4 flex flex-col gap-4">
        {model.steps.map((step) => (
          <StepMatchCard key={step.id} step={step} workflowId={model.id} />
        ))}
      </div>
    </div>
  );
}
