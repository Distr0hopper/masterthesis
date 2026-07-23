import {Card, CardContent} from "@/components/ui/card.tsx";
import {authTransformer, type LoginFormData, loginFormSchema, useLogin} from "@/api/auth";
import { useForm } from 'react-hook-form';
import {zodResolver} from "@hookform/resolvers/zod";
import {Input} from "@/components/ui/input.tsx";
import {Button} from "@/components/ui/button.tsx";
import {Link, useNavigate} from "react-router-dom";
import {Label} from "@/components/ui/label.tsx";
import {getErrorMessage} from "@/lib/errors";

export default function LoginPage() {
  const navigate = useNavigate();
  const { mutate, isPending } = useLogin();
  const { register, handleSubmit, formState: { errors }, setError } = useForm<LoginFormData>({
    resolver: zodResolver(loginFormSchema),
    defaultValues: authTransformer.getInitialLoginFormValues(),
  });

  const onSubmit = (data: LoginFormData) => {
    const loginDto = authTransformer.formToLoginDto(data);
    mutate(loginDto, {
      onSuccess: () => {
        navigate('/')
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
      <p className="mt-1 text-slate-500">Sign in to your account</p>

      <Card className="mt-6 w-full shadow-lg">
        <CardContent className="pt-6">
          <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
            {errors.root && (
              <p className="rounded-md bg-error px-3 py-2 text-sm text-error-foreground">{errors.root.message}</p>
            )}

            <div className="flex flex-col gap-2">
              <Label htmlFor="email">Email</Label>
              <Input {...register('email')} type="email" id="email" placeholder="researcher@uni-wuerzburg.de" />
              {errors.email && <p className="text-sm text-error-foreground">{errors.email.message}</p>}
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="password">Password</Label>
              <Input {...register('password')} type="password" id="password" placeholder="••••••••" />
              {errors.password && <p className="text-sm text-error-foreground">{errors.password.message}</p>}
            </div>

            <Button type="submit" className="w-full bg-jmu-blue-800 hover:bg-jmu-blue-800/90" disabled={isPending}>
              {isPending ? 'Logging in...' : 'Login'}
            </Button>
          </form>
        </CardContent>
      </Card>

      <p className="mt-6 text-sm text-slate-500">
        No account?{' '}
        <Link to="/register" className="font-semibold text-jmu-blue-800 hover:underline">
          Register
        </Link>
      </p>
    </div>
  );
}