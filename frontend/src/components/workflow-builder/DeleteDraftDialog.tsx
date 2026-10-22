import { toast } from 'sonner';
import { ConfirmDeleteDialog } from '@/components/common/ConfirmDeleteDialog';
import { useDeleteDraft, type WorkflowDraftListItemDto } from '@/api/workflow-drafts';
import { getErrorMessage } from '@/lib/errors';

interface DeleteDraftDialogProps {
  draft: WorkflowDraftListItemDto;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDeleted?: () => void;
}

export function DeleteDraftDialog({ draft, open, onOpenChange, onDeleted }: DeleteDraftDialogProps) {
  const { mutate, isPending } = useDeleteDraft();

  const handleDelete = (deleteLinkedWorkflow: boolean) => {
    mutate(
      { id: draft.id, deleteLinkedWorkflow },
      {
        onSuccess: () => {
          toast.success(
            deleteLinkedWorkflow ? 'Workflow and its unpublished versions deleted' : 'Workflow deleted',
          );
          onOpenChange(false);
          onDeleted?.();
        },
        onError: (error) => toast.error(getErrorMessage(error, 'Could not delete this workflow.')),
      },
    );
  };

  return (
    <ConfirmDeleteDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Delete workflow?"
      description={`This will permanently remove "${draft.name}" from your saved workflows.`}
      linkedOption={
        draft.linkedWorkflowId
          ? {
              label: (
                <>
                  Also delete its unpublished versions in <span className="font-medium">My Workflows</span>.
                  Published or deprecated versions always stay - others may already use them.
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
