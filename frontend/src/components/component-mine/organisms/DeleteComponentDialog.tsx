import { Link } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { ConfirmDeleteDialog } from '@/components/common/ConfirmDeleteDialog';
import {
  useComponentDeletionImpact,
  useDeleteComponent,
  type ComponentDeletionImpactDto,
  type ComponentDisplayModel,
} from '@/api/components';
import { getLink } from '@/api/permissions';
import { WorkflowStatus, workflowKeys } from '@/api/workflows';
import { draftKeys } from '@/api/workflow-drafts';
import { getErrorMessage } from '@/lib/errors';
import { ROUTES } from '@/lib/routes';

interface DeleteComponentDialogProps {
  component: ComponentDisplayModel;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDeleted?: () => void;
}

function plural(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? '' : 's'}`;
}

/** Where this version is still used - the delete goes ahead regardless, this just says what it unmatches. */
function UsageWarning({ impact }: { impact: ComponentDeletionImpactDto }) {
  const workflowCount = impact.workflows.length + impact.hiddenWorkflowCount;
  const draftCount = impact.drafts.length + impact.otherDraftCount;
  if (workflowCount === 0 && draftCount === 0) return null;

  return (
    <div role="alert" className="space-y-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
      <div className="flex items-start gap-2 font-medium">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" aria-hidden />
        <span>This version is still in use.</span>
      </div>

      {workflowCount > 0 && (
        <div>
          <p>
            Used by {plural(workflowCount, 'workflow')}. Their steps will be unmatched, and published workflows are
            reverted to pending validation until a new component is picked.
          </p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5">
            {impact.workflows.map((workflow) => (
              <li key={workflow.id}>
                <Link to={ROUTES.workflowDetail(workflow.id)} className="underline" target="_blank" rel="noreferrer">
                  {workflow.name}
                </Link>
                {workflow.status === WorkflowStatus.VALIDATED && ' (published)'}
              </li>
            ))}
            {impact.hiddenWorkflowCount > 0 && (
              <li>{plural(impact.hiddenWorkflowCount, 'private workflow')} of other users</li>
            )}
          </ul>
        </div>
      )}

      {draftCount > 0 && (
        <div>
          <p>
            On the canvas of {plural(draftCount, 'builder draft')}. It will be flagged there as removed and has to be
            replaced before the draft can be exported.
          </p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5">
            {impact.drafts.map((draft) => (
              <li key={draft.id}>
                <Link to={ROUTES.builderWorkflow(draft.id)} className="underline" target="_blank" rel="noreferrer">
                  {draft.name}
                </Link>
              </li>
            ))}
            {impact.otherDraftCount > 0 && <li>{plural(impact.otherDraftCount, 'draft')} of other users</li>}
          </ul>
        </div>
      )}
    </div>
  );
}

export function DeleteComponentDialog({ component, open, onOpenChange, onDeleted }: DeleteComponentDialogProps) {
  const queryClient = useQueryClient();
  const { mutate, isPending } = useDeleteComponent();
  const { data: impact, isLoading: isLoadingImpact } = useComponentDeletionImpact(
    getLink(component._links, 'deletionImpact'),
    open,
  );

  const handleDelete = () => {
    mutate(getLink(component._links, 'delete')!, {
      onSuccess: () => {
        toast.success(`${component.name} v${component.version} deleted`);
        // the delete unmatched workflow steps and left drafts with a removed component, so
        // every cached workflow or draft view is stale now. Invalidated here, not in
        // useDeleteComponent: api/workflows already imports api/components
        queryClient.invalidateQueries({ queryKey: workflowKeys.all });
        queryClient.invalidateQueries({ queryKey: draftKeys.all });
        onOpenChange(false);
        onDeleted?.();
      },
      onError: (error) => {
        toast.error(getErrorMessage(error));
      },
    });
  };

  return (
    <ConfirmDeleteDialog
      open={open}
      onOpenChange={onOpenChange}
      title={`Delete ${component.name}?`}
      description={
        <>
          This will permanently delete version {component.version}. If this is the only version, the component will be
          removed from the repository entirely. This action cannot be undone.
        </>
      }
      onConfirm={handleDelete}
      isPending={isPending}
    >
      {isLoadingImpact && <p className="text-sm text-slate-500">Checking where this version is used...</p>}
      {impact && <UsageWarning impact={impact} />}
    </ConfirmDeleteDialog>
  );
}
