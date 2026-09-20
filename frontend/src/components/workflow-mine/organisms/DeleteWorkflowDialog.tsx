import { toast } from 'sonner';
import { ConfirmDeleteDialog } from '@/components/common/ConfirmDeleteDialog';
import { useDeleteWorkflow, type WorkflowDisplayModel } from '@/api/workflows';
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

  const handleDelete = () => {
    mutate(getLink(workflow._links, 'delete')!, {
      onSuccess: () => {
        toast.success('Workflow deleted');
        onOpenChange(false);
        onDeleted?.();
      },
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  };

  return (
    <ConfirmDeleteDialog
      open={open}
      onOpenChange={onOpenChange}
      title={`Delete workflow "${workflow.name}"?`}
      description="This will permanently delete the workflow. This action cannot be undone."
      onConfirm={handleDelete}
      isPending={isPending}
    />
  );
}
