import { toast } from 'sonner';
import { ConfirmDeleteDialog } from '@/components/common/ConfirmDeleteDialog';
import { useDeleteComponent, type ComponentDisplayModel } from '@/api/components';
import { getLink } from '@/api/permissions';
import { getErrorMessage } from '@/lib/errors';

interface DeleteComponentDialogProps {
  component: ComponentDisplayModel;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDeleted?: () => void;
}

export function DeleteComponentDialog({ component, open, onOpenChange, onDeleted }: DeleteComponentDialogProps) {
  const { mutate, isPending } = useDeleteComponent();

  const handleDelete = () => {
    mutate(getLink(component._links, 'delete')!, {
      onSuccess: () => {
        toast.success(`${component.name} v${component.version} deleted`);
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
    />
  );
}
