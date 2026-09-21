import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog.tsx';
import { Textarea } from '@/components/ui/textarea.tsx';
import { Button } from '@/components/ui/button.tsx';
import { Label } from '@/components/ui/label.tsx';
import {
  componentTransformer,
  updateComponentFormSchema,
  useUpdateComponentDescription,
  useUpdateComponentDomains,
  type ComponentDisplayModel,
  type UpdateComponentFormData,
} from '@/api/components';
import { getLink } from '@/api/permissions';
import { getErrorMessage } from '@/lib/errors';
import { DomainMultiSelect } from '@/components/common/DomainMultiSelect';

interface EditComponentDialogProps {
  component: ComponentDisplayModel;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function EditComponentDialog({ component, open, onOpenChange }: EditComponentDialogProps) {
  const { mutateAsync: updateDescription } = useUpdateComponentDescription();
  const { mutateAsync: updateDomains } = useUpdateComponentDomains();
  const {
    control,
    register,
    handleSubmit,
    formState: { errors, dirtyFields, isSubmitting },
    setError,
  } = useForm<UpdateComponentFormData>({
    resolver: zodResolver(updateComponentFormSchema),
    values: componentTransformer.getInitialUpdateFormValues(component),
  });

  const onSubmit = async (data: UpdateComponentFormData) => {
    if (!dirtyFields.description && !dirtyFields.domains) {
      onOpenChange(false);
      return;
    }

    try {
      if (dirtyFields.description) {
        await updateDescription({
          link: getLink(component._links, 'updateDescription')!,
          description: data.description || null,
        });
      }
      if (dirtyFields.domains && data.domains?.length) {
        await updateDomains({ link: getLink(component._links, 'updateDomain')!, domains: data.domains });
      }
      toast.success(`${component.name} updated`);
      onOpenChange(false);
    } catch (error) {
      setError('root', { message: getErrorMessage(error) });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit {component.name}</DialogTitle>
        </DialogHeader>

        <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
          {errors.root && <p className="rounded-md bg-error px-3 py-2 text-sm text-error-foreground">{errors.root.message}</p>}

          <Controller
            control={control}
            name="domains"
            render={({ field }) => (
              <DomainMultiSelect value={field.value ?? []} onChange={field.onChange} error={errors.domains?.message} />
            )}
          />

          <div className="flex flex-col gap-2">
            <Label htmlFor="edit-description">
              Description <span className="font-normal text-slate-500">(optional)</span>
            </Label>
            <Textarea {...register('description')} id="edit-description" rows={4} />
            {errors.description && <p className="text-sm text-error-foreground">{errors.description.message}</p>}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90" disabled={isSubmitting}>
              {isSubmitting ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
