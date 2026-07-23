import {authTransformer, type RegisterFormData, registerFormSchema, useRegister} from "@/api/auth";
import {useForm} from "react-hook-form";
import {zodResolver} from "@hookform/resolvers/zod";
import {Card, CardContent} from "@/components/ui/card.tsx";
import {Label} from "@/components/ui/label.tsx";
import {Input} from "@/components/ui/input.tsx";
import {Button} from "@/components/ui/button.tsx";
import {Link, useNavigate} from "react-router-dom";
import {getErrorMessage} from "@/lib/errors";

export default function RegisterPage() {
  const navigate = useNavigate();
  const { mutate, isPending } = useRegister();
  const { register, handleSubmit, formState: {errors}, setError } = useForm<RegisterFormData>({
    resolver: zodResolver(registerFormSchema),
    defaultValues: authTransformer.getInitialRegisterFormValues()
  });

  const onSubmit = (data: RegisterFormData) => {
    mutate(authTransformer.formToRegisterDto(data), {
      onSuccess: () => {
        navigate('/login');
      },
      onError: (error) => {
        setError('root', {message: getErrorMessage(error)});
      }
    });
  }

  return (
      <div className="mx-auto flex min-h-[70vh] max-w-md flex-col items-center justify-center">
        <img src="/icons/Icon-S-dark.svg" alt="" />
        <h1 className="mt-4 text-2xl font-semibold text-slate-900">JMU Component Repository</h1>
        <p className="mt-1 text-slate-500"> Create an account</p>

        <Card className="mt-6 w-full shadow-lg">
          <CardContent className="pt-6">
            <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
              {errors.root && (
                  <p className="rounded-md bg-error px-3 py-2 text-sm text-error-foreground">{errors.root.message}</p>
              )}

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
                <Label htmlFor="email">Email</Label>
                <Input {...register('email')} type="email" id="email" placeholder="researcher@uni-wuerzburg.de" />
                {errors.email && <p className="text-sm text-error-foreground">{errors.email.message}</p>}
              </div>

              <div className="flex flex-col gap-2">
                <Label htmlFor="password">Password</Label>
                <Input {...register('password')} type="password" id="password" placeholder="Minimum 8 characters" />
                {errors.password && <p className="text-sm text-error-foreground">{errors.password.message}</p>}
              </div>

              <div className="flex flex-col gap-2">
                <Label htmlFor="confirmPassword">Confirm Password</Label>
                <Input {...register('confirmPassword')} type="password" id="confirmPassword" placeholder="Repeat password" />
                {errors.confirmPassword && <p className="text-sm text-error-foreground">{errors.confirmPassword.message}</p>}
              </div>

              <Button type="submit" className="w-full bg-jmu-blue-800 hover:bg-jmu-blue-800/90" disabled={isPending}>
                {isPending ? 'Creating account...' : 'Register'}
              </Button>
            </form>
          </CardContent>
        </Card>

        <p className="mt-6 text-sm text-slate-500">
          Already have an account?{' '}
          <Link to="/login" className="font-semibold text-jmu-blue-800 hover:underline">
            Login
          </Link>
        </p>
      </div>
  );
}