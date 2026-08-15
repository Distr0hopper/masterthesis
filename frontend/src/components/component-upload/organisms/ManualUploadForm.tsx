import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Input } from '@/components/ui/input.tsx';
import { Textarea } from '@/components/ui/textarea.tsx';
import { Button } from '@/components/ui/button.tsx';
import { Label } from '@/components/ui/label.tsx';
import {
  componentTransformer,
  uploadComponentFormSchema,
  useUploadComponent,
  type UploadComponentFormData,
} from '@/api/components';
import { getErrorMessage } from '@/lib/errors';
import { ROUTES } from '@/lib/routes';
import { DomainSelect } from '../common/DomainSelect';
import { CwlFileDropzone } from '../common/CwlFileDropzone';

export function ManualUploadForm() {
  const navigate = useNavigate();
  const { mutate, isPending } = useUploadComponent();
  const {
    control,
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<UploadComponentFormData>({
    resolver: zodResolver(uploadComponentFormSchema),
    defaultValues: componentTransformer.getInitialUploadFormValues(),
  });

  const onSubmit = (data: UploadComponentFormData) => {
    const dto = componentTransformer.formToCreateDto(data);
    mutate(
      { file: data.cwlFile, dto },
      {
        onSuccess: (created) => {
          toast.success(`${created.name} created`);
          navigate(ROUTES.componentDetail(created.id));
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
        name="cwlFile"
        render={({ field }) => (
          <CwlFileDropzone value={field.value ?? null} onChange={field.onChange} error={errors.cwlFile?.message} />
        )}
      />

      <div className="flex flex-col gap-2">
        <Label htmlFor="name">Component Name</Label>
        <Input {...register('name')} id="name" placeholder="e.g. remove-outliers" />
        {errors.name && <p className="text-sm text-error-foreground">{errors.name.message}</p>}
      </div>

      <Controller
        control={control}
        name="domain"
        render={({ field }) => <DomainSelect value={field.value} onChange={field.onChange} error={errors.domain?.message} />}
      />

      <div className="flex flex-col gap-2">
        <Label htmlFor="description">
          Description <span className="font-normal text-slate-500">(optional)</span>
        </Label>
        <Textarea {...register('description')} id="description" placeholder="Brief description..." rows={4} />
        {errors.description && <p className="text-sm text-error-foreground">{errors.description.message}</p>}
      </div>

      <Button type="submit" className="w-full bg-jmu-blue-800 hover:bg-jmu-blue-800/90" disabled={isPending}>
        {isPending ? 'Creating...' : 'Create Component'}
      </Button>
    </form>
  );
}
