import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Input } from '@/components/ui/input.tsx';
import { Button } from '@/components/ui/button.tsx';
import { Label } from '@/components/ui/label.tsx';
import { getErrorMessage } from '@/lib/errors';
import { useAuthStore } from '@/store/auth.store';
import { type UpdateProfileFormData, updateProfileFormSchema, useUpdateProfile, usersTransformer } from '@/api/users';

export default function ProfilePage() {
  const user = useAuthStore((state) => state.user);
  const [saved, setSaved] = useState(false);
  const { mutate, isPending } = useUpdateProfile();
  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<UpdateProfileFormData>({
    resolver: zodResolver(updateProfileFormSchema),
    defaultValues: usersTransformer.getInitialUpdateProfileFormValues(user),
  });

  const onSubmit = (data: UpdateProfileFormData) => {
    setSaved(false);
    const dto = usersTransformer.formToUpdateUserDto(data);
    mutate(dto, {
      onSuccess: () => setSaved(true),
      onError: (error) => {
        setError('root', { message: getErrorMessage(error) });
      },
    });
  };

  return (
    <div className="mx-auto flex max-w-md flex-col items-center">
      <h1 className="text-2xl font-semibold text-slate-900">Your profile</h1>
      <p className="mt-1 text-slate-500">Complete your profile so others know who you are.</p>

      <Card className="mt-6 w-full shadow-lg">
        <CardContent className="pt-6">
          <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
            {errors.root && <p className="rounded-md bg-error px-3 py-2 text-sm text-error-foreground">{errors.root.message}</p>}
            {saved && <p className="rounded-md bg-jmu-blue-50 px-3 py-2 text-sm text-jmu-blue-800">Profile saved.</p>}

            <div className="flex flex-col gap-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" value={user?.email ?? ''} disabled />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="firstName">First Name</Label>
                <Input {...register('firstName')} id="firstName" placeholder="Jane" />
                {errors.firstName && <p className="text-sm text-error-foreground">{errors.firstName.message}</p>}
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="lastName">Last Name</Label>
                <Input {...register('lastName')} id="lastName" placeholder="Doe" />
                {errors.lastName && <p className="text-sm text-error-foreground">{errors.lastName.message}</p>}
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="affiliation">Affiliation</Label>
              <Input {...register('affiliation')} id="affiliation" placeholder="University of Würzburg" />
              {errors.affiliation && <p className="text-sm text-error-foreground">{errors.affiliation.message}</p>}
            </div>

            <Button type="submit" className="w-full bg-jmu-blue-800 hover:bg-jmu-blue-800/90" disabled={isPending}>
              {isPending ? 'Saving...' : 'Save profile'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}