import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Input } from '@/components/ui/input.tsx';
import { Textarea } from '@/components/ui/textarea.tsx';
import { Button } from '@/components/ui/button.tsx';
import {
  componentTransformer,
  uploadComponentFormSchema,
  useUploadComponent,
  type ComponentDetailDto,
  type UploadComponentFormData,
} from '@/api/components';
import { getErrorMessage } from '@/lib/errors';
import { ROUTES } from '@/lib/routes';
import { FileDropzone } from '@/components/common/FileDropzone';
import { FormField } from '@/components/common/FormField';
import { DomainSelect } from '../common/DomainSelect';

interface ManualUploadFormProps {
  // when provided, replaces the default post-upload navigation - used to embed this form
  // in contexts like the workflow step picker, where navigating away would abandon
  // whatever page it was opened from
  onSuccess?: (created: ComponentDetailDto) => void;
}

export function ManualUploadForm({ onSuccess }: ManualUploadFormProps) {
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
          if (onSuccess) {
            onSuccess(created);
          } else {
            navigate(ROUTES.componentDetail(created.id));
          }
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
          <FileDropzone
            value={field.value ?? null}
            onChange={field.onChange}
            accept=".cwl"
            label="CWL File"
            error={errors.cwlFile?.message}
          />
        )}
      />

      <FormField htmlFor="name" label="Component Name" error={errors.name?.message}>
        <Input {...register('name')} id="name" placeholder="e.g. remove-outliers" />
      </FormField>

      <Controller
        control={control}
        name="domain"
        render={({ field }) => <DomainSelect value={field.value} onChange={field.onChange} error={errors.domain?.message} />}
      />

      <FormField htmlFor="description" label="Description" optional error={errors.description?.message}>
        <Textarea {...register('description')} id="description" placeholder="Brief description..." rows={4} />
      </FormField>

      <Button type="submit" className="w-full bg-jmu-blue-800 hover:bg-jmu-blue-800/90" disabled={isPending}>
        {isPending ? 'Creating...' : 'Create Component'}
      </Button>
    </form>
  );
}
