import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Input } from '@/components/ui/input.tsx';
import { Textarea } from '@/components/ui/textarea.tsx';
import { Button } from '@/components/ui/button.tsx';
import { Label } from '@/components/ui/label.tsx';
import { uploadWorkflowFormSchema, useUploadWorkflow, workflowTransformer, type UploadWorkflowFormData } from '@/api/workflows';
import { getErrorMessage } from '@/lib/errors';
import { ROUTES } from '@/lib/routes';
import { DomainMultiSelect } from '../common/DomainMultiSelect';
import { WorkflowZipDropzone } from '../common/WorkflowZipDropzone';

export function WorkflowUploadForm() {
  const navigate = useNavigate();
  const { mutate, isPending } = useUploadWorkflow();
  const {
    control,
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<UploadWorkflowFormData>({
    resolver: zodResolver(uploadWorkflowFormSchema),
    defaultValues: workflowTransformer.getInitialUploadFormValues(),
  });

  const onSubmit = (data: UploadWorkflowFormData) => {
    mutate(
      { file: data.zipFile, dto: { name: data.name, domains: data.domains, description: data.description || null } },
      {
        onSuccess: (created) => {
          toast.success(`${created.name} created`);
          navigate(ROUTES.workflowDetail(created.id));
        },
        onError: (error) => {
          setError('root', { message: getErrorMessage(error) });
        },
      },
    );
  };

  return (
    <form className="flex flex-col gap-6" onSubmit={handleSubmit(onSubmit)} noValidate>
      {errors.root && <p className="rounded-md bg-error px-3 py-2 text-sm text-error-foreground">{errors.root.message}</p>}

      <Controller
        control={control}
        name="zipFile"
        render={({ field }) => (
          <WorkflowZipDropzone value={field.value ?? null} onChange={field.onChange} error={errors.zipFile?.message} />
        )}
      />

      <div className="flex flex-col gap-2">
        <Label htmlFor="name">Workflow Name</Label>
        <Input {...register('name')} id="name" placeholder="e.g. Outlier Removal + Thinning Pipeline" />
        {errors.name && <p className="text-sm text-error-foreground">{errors.name.message}</p>}
      </div>

      <Controller
        control={control}
        name="domains"
        render={({ field }) => (
          <DomainMultiSelect value={field.value} onChange={field.onChange} error={errors.domains?.message} />
        )}
      />

      <div className="flex flex-col gap-2">
        <Label htmlFor="description">
          Description <span className="font-normal text-slate-500">(optional)</span>
        </Label>
        <Textarea {...register('description')} id="description" placeholder="Brief description..." rows={4} />
        {errors.description && <p className="text-sm text-error-foreground">{errors.description.message}</p>}
      </div>

      <Button type="submit" className="w-full bg-jmu-blue-800 hover:bg-jmu-blue-800/90" disabled={isPending}>
        {isPending ? 'Creating...' : 'Create Workflow'}
      </Button>
    </form>
  );
}
