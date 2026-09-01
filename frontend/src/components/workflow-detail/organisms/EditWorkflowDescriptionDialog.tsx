import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog.tsx';
import { Textarea } from '@/components/ui/textarea.tsx';
import { Button } from '@/components/ui/button.tsx';
import { Label } from '@/components/ui/label.tsx';
import {
  updateWorkflowDescriptionFormSchema,
  useUpdateWorkflowDescription,
  workflowTransformer,
  type UpdateWorkflowDescriptionFormData,
  type WorkflowDetailDisplayModel,
} from '@/api/workflows';
import { getLink } from '@/api/permissions';
import { getErrorMessage } from '@/lib/errors';

interface EditWorkflowDescriptionDialogProps {
  workflow: WorkflowDetailDisplayModel;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function EditWorkflowDescriptionDialog({ workflow, open, onOpenChange }: EditWorkflowDescriptionDialogProps) {
  const { mutate, isPending } = useUpdateWorkflowDescription();
  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<UpdateWorkflowDescriptionFormData>({
    resolver: zodResolver(updateWorkflowDescriptionFormSchema),
    values: workflowTransformer.getInitialUpdateDescriptionFormValues(workflow),
  });

  const onSubmit = (data: UpdateWorkflowDescriptionFormData) => {
    mutate(
      { link: getLink(workflow._links, 'updateDescription')!, description: data.description || null },
      {
        onSuccess: () => {
          toast.success(`${workflow.name} updated`);
          onOpenChange(false);
        },
        onError: (error) => {
          setError('root', { message: getErrorMessage(error) });
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit description</DialogTitle>
        </DialogHeader>

        <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
          {errors.root && <p className="rounded-md bg-error px-3 py-2 text-sm text-error-foreground">{errors.root.message}</p>}

          <div className="flex flex-col gap-2">
            <Label htmlFor="edit-workflow-description">
              Description <span className="font-normal text-slate-500">(optional)</span>
            </Label>
            <Textarea {...register('description')} id="edit-workflow-description" rows={4} />
            {errors.description && <p className="text-sm text-error-foreground">{errors.description.message}</p>}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90" disabled={isPending}>
              {isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
