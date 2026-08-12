import { toast } from 'sonner';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog.tsx';
import { Button } from '@/components/ui/button.tsx';
import { useDeleteComponent, type ComponentDisplayModel } from '@/api/components';
import { getErrorMessage } from '@/lib/errors';

interface DeleteComponentDialogProps {
  component: ComponentDisplayModel;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DeleteComponentDialog({ component, open, onOpenChange }: DeleteComponentDialogProps) {
  const { mutate, isPending } = useDeleteComponent();

  const handleDelete = () => {
    mutate(component.id, {
      onSuccess: () => {
        toast.success(`${component.name} v${component.version} deleted`);
        onOpenChange(false);
      },
      onError: (error) => {
        toast.error(getErrorMessage(error));
      },
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete {component.name}?</DialogTitle>
          <DialogDescription>
            This will permanently delete version {component.version}. If this is the only version, the component will be
            removed from the repository entirely. This action cannot be undone.
          </DialogDescription>
        </DialogHeader>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            Cancel
          </Button>
          <Button type="button" variant="destructive" onClick={handleDelete} disabled={isPending}>
            {isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
