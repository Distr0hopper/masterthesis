import { toast } from 'sonner';
import { ConfirmDeleteDialog } from '@/components/common/ConfirmDeleteDialog';
import { useDeleteWorkflow, WorkflowSource, type WorkflowDisplayModel } from '@/api/workflows';
import { getLink } from '@/api/permissions';
import { getErrorMessage } from '@/lib/errors';

interface DeleteWorkflowDialogProps {
  workflow: WorkflowDisplayModel;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDeleted?: () => void;
}

export function DeleteWorkflowDialog({ workflow, open, onOpenChange, onDeleted }: DeleteWorkflowDialogProps) {
  const { mutate, isPending } = useDeleteWorkflow();

  // only offer the cascade when there is something on the other side to delete: the
  // workflow came from the builder and its draft still exists (draftId is ON DELETE SET
  // NULL, so a draft already deleted from the builder leaves this null)
  const hasLinkedDraft =
    workflow.source === WorkflowSource.WORKFLOW_BUILDER && workflow.draftId !== null;

  const handleDelete = (deleteLinkedDraft: boolean) => {
    mutate(
      { link: getLink(workflow._links, 'delete')!, deleteLinkedDraft },
      {
        onSuccess: () => {
          toast.success(deleteLinkedDraft ? 'Workflow and builder canvas deleted' : 'Workflow deleted');
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
      title={`Delete workflow "${workflow.name}"?`}
      description="This will permanently delete the workflow. This action cannot be undone."
      linkedOption={
        hasLinkedDraft
          ? {
              label: (
                <>
                  Also delete its canvas in the <span className="font-medium">Workflow Builder</span>.
                  Leave unchecked to keep editing it there - saving again will create a new
                  copy here.
                </>
              ),
            }
          : undefined
      }
      onConfirm={handleDelete}
      isPending={isPending}
    />
  );
}
