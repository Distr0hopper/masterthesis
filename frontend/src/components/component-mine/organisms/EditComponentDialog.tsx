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
  useUpdateComponent,
  type ComponentDisplayModel,
  type UpdateComponentFormData,
} from '@/api/components';
import { getErrorMessage } from '@/lib/errors';
import { DomainSelect } from '@/components/component-upload/common/DomainSelect';

interface EditComponentDialogProps {
  component: ComponentDisplayModel;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function EditComponentDialog({ component, open, onOpenChange }: EditComponentDialogProps) {
  const { mutate, isPending } = useUpdateComponent();
  const {
    control,
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<UpdateComponentFormData>({
    resolver: zodResolver(updateComponentFormSchema),
    values: componentTransformer.getInitialUpdateFormValues(component),
  });

  const onSubmit = (data: UpdateComponentFormData) => {
    const dto = componentTransformer.formToUpdateDto(data);
    mutate(
      { id: component.id, dto },
      {
        onSuccess: () => {
          toast.success(`${component.name} updated`);
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
          <DialogTitle>Edit {component.name}</DialogTitle>
        </DialogHeader>

        <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
          {errors.root && <p className="rounded-md bg-error px-3 py-2 text-sm text-error-foreground">{errors.root.message}</p>}

          <Controller
            control={control}
            name="domain"
            render={({ field }) => (
              <DomainSelect value={field.value ?? ''} onChange={field.onChange} error={errors.domain?.message} />
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
            <Button type="submit" className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90" disabled={isPending}>
              {isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
