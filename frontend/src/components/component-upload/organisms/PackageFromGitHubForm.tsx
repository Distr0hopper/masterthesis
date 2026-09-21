import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Input } from '@/components/ui/input.tsx';
import { Button } from '@/components/ui/button.tsx';
import { Label } from '@/components/ui/label.tsx';
import {
  componentTransformer,
  packageComponentFormSchema,
  usePackageComponent,
  type PackageComponentFormData,
} from '@/api/components';
import { getErrorMessage } from '@/lib/errors';
import { ROUTES } from '@/lib/routes';
import { DomainMultiSelect } from '@/components/common/DomainMultiSelect';

export function PackageFromGitHubForm() {
  const navigate = useNavigate();
  const { mutate, isPending } = usePackageComponent();
  const {
    control,
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<PackageComponentFormData>({
    resolver: zodResolver(packageComponentFormSchema),
    defaultValues: componentTransformer.getInitialPackageFormValues(),
  });

  const onSubmit = (data: PackageComponentFormData) => {
    const dto = componentTransformer.formToPackageDto(data);
    mutate(dto, {
      onSuccess: (created) => {
        toast.success(`${created.name} packaged`);
        navigate(ROUTES.componentDetail(created.id));
      },
      onError: (error) => {
        setError('root', { message: getErrorMessage(error) });
      },
    });
  };

  return (
    <form className="flex flex-col gap-6" onSubmit={handleSubmit(onSubmit)} noValidate>
      {errors.root && <p className="rounded-md bg-error px-3 py-2 text-sm text-error-foreground">{errors.root.message}</p>}

      <div className="rounded-md border border-jmu-blue-200 bg-jmu-blue-50 px-4 py-3 text-sm text-jmu-blue-900">
        <p className="font-semibold">Automated packaging</p>
        <p className="mt-1">
          Provide a MoveApps GitHub repository URL. The system will clone the repository, read{' '}
          <code className="rounded bg-jmu-blue-100 px-1 py-0.5 font-mono text-xs">appspec.json</code>, and automatically
          generate a CWL CommandLineTool definition and Dockerfile.
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="repoUrl">Repository URL</Label>
        <Input {...register('repoUrl')} id="repoUrl" placeholder="https://github.com/movestore/Remove_Outliers" />
        {errors.repoUrl && <p className="text-sm text-error-foreground">{errors.repoUrl.message}</p>}
      </div>

      <Controller
        control={control}
        name="domains"
        render={({ field }) => (
          <DomainMultiSelect value={field.value ?? []} onChange={field.onChange} error={errors.domains?.message} />
        )}
      />

      <Button type="submit" className="w-full bg-jmu-blue-800 hover:bg-jmu-blue-800/90" disabled={isPending}>
        {isPending ? 'Packaging...' : 'Package Component'}
      </Button>
    </form>
  );
}
