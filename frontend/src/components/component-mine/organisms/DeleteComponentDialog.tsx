import { Link } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { ConfirmDeleteDialog } from '@/components/common/ConfirmDeleteDialog';
import { PublicAncestors } from '@/components/common/PublicAncestors';
import {
  ComponentSource,
  ComponentStatus,
  isRetractBlocked,
  ownPublishedAncestors,
  useComponentImpact,
  useDeleteComponent,
  type ComponentImpactDto,
  type ComponentDisplayModel,
} from '@/api/components';
import { canDeprecate, getLink } from '@/api/permissions';
import { draftKeys } from '@/api/workflow-drafts';
import { getErrorMessage } from '@/lib/errors';
import { ROUTES } from '@/lib/routes';

interface DeleteComponentDialogProps {
  component: ComponentDisplayModel;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDeleted?: () => void;
  /** opens the deprecate dialog - offered when deleting is blocked */
  onDeprecateInstead: () => void;
}

function plural(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? '' : 's'}`;
}

/** Where this version is still used - what the delete unmatches. Public workflows above it are PublicAncestors' part. */
function UsageWarning({ impact }: { impact: ComponentImpactDto }) {
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
            Used by {plural(workflowCount, 'workflow')}. Their steps will be unmatched until a new component is
            picked.
          </p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5">
            {impact.workflows.map((workflow) => (
              <li key={workflow.id}>
                <Link to={ROUTES.workflowDetail(workflow.id)} className="underline" target="_blank" rel="noreferrer">
                  {workflow.name} v{workflow.version}
                </Link>
                {workflow.status !== ComponentStatus.DRAFT && ` (${workflow.status})`}
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

/**
 * Deleting one version of either kind. Both can be in use - a tool by workflows, a
 * workflow by the workflows nesting it - so both get the usage warning. A builder
 * workflow additionally offers to take the canvas it was synced from along.
 */
export function DeleteComponentDialog({
  component,
  open,
  onOpenChange,
  onDeleted,
  onDeprecateInstead,
}: DeleteComponentDialogProps) {
  const queryClient = useQueryClient();
  const { mutate, isPending } = useDeleteComponent();
  const { data: impact, isLoading: isLoadingImpact } = useComponentImpact(getLink(component._links, 'impact'), open);
  // another user's public workflow runs it - taking it out of public view would break theirs
  const blocked = isRetractBlocked(impact);
  // the user's own published workflows above it become drafts with it - confirmed by deleting
  const ownParents = impact ? ownPublishedAncestors(impact).length : 0;

  // only offer the cascade when there is something on the other side to delete: the
  // workflow came from the builder and its draft still exists (draftId is ON DELETE SET
  // NULL, so a draft already deleted from the builder leaves this null)
  const hasLinkedDraft =
    component.kind === 'workflow' &&
    component.source === ComponentSource.WORKFLOW_BUILDER &&
    component.draftId !== null;

  const handleDelete = (deleteLinkedDraft: boolean) => {
    mutate(
      { link: getLink(component._links, 'delete')!, deleteLinkedDraft, unpublishParents: ownParents > 0 },
      {
        onSuccess: () => {
          toast.success(
            deleteLinkedDraft
              ? `${component.name} v${component.version} and its builder canvas deleted`
              : `${component.name} v${component.version} deleted`,
          );
          // the delete unmatched workflow steps and left drafts with a removed component,
          // so every cached draft view is stale now
          queryClient.invalidateQueries({ queryKey: draftKeys.all });
          onOpenChange(false);
          onDeleted?.();
        },
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  };

  return (
    <ConfirmDeleteDialog
      open={open}
      onOpenChange={onOpenChange}
      title={`Delete ${component.name}?`}
      description={
        <>
          This will permanently delete version {component.version}. If this is the only version, the{' '}
          {component.kindDisplay.toLowerCase()} will be removed from the repository entirely. This action cannot be
          undone.
        </>
      }
      linkedOption={
        hasLinkedDraft
          ? {
              label: (
                <>
                  Also delete its canvas in the <span className="font-medium">Workflow Builder</span>. Leave unchecked
                  to keep editing it there - saving again will create a new copy here.
                </>
              ),
            }
          : undefined
      }
      onConfirm={handleDelete}
      isPending={isPending || isLoadingImpact}
      blocked={blocked}
      blockedAlternative={
        canDeprecate(component._links) && component.status === ComponentStatus.PUBLISHED
          ? { label: 'Deprecate instead', onSelect: onDeprecateInstead }
          : undefined
      }
      confirmLabel={ownParents > 0 ? `Delete and unpublish ${ownParents}` : 'Delete'}
    >
      {isLoadingImpact && <p className="text-sm text-slate-500">Checking where this version is used...</p>}
      {impact && <PublicAncestors impact={impact} verb="Deleting" />}
      {impact && !blocked && <UsageWarning impact={impact} />}
    </ConfirmDeleteDialog>
  );
}
