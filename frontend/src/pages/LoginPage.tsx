import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Card, CardContent } from '@/components/ui/card.tsx';
import {
    authTransformer,
    type RequestOtpFormData,
    requestOtpFormSchema,
    type VerifyOtpFormData,
    verifyOtpFormSchema,
    useRequestOtp,
    useVerifyOtp, type RequestOtpResponseDto, type RequestOtpDto,
} from '@/api/auth';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Input } from '@/components/ui/input.tsx';
import { Button } from '@/components/ui/button.tsx';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Label } from '@/components/ui/label.tsx';
import { getErrorMessage } from '@/lib/errors';
import { ROUTES } from '@/lib/routes';
import { safeRedirect } from '@/api/auth/session';

function EmailStep({ onRequested }: { onRequested: (email: string, cooldownSeconds: number) => void }) {
  const { mutate, isPending } = useRequestOtp();
  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<RequestOtpFormData>({
    resolver: zodResolver(requestOtpFormSchema),
    defaultValues: authTransformer.getInitialRequestOtpFormValues(),
  });

  const onSubmit = (data: RequestOtpFormData) => {
    const dto: RequestOtpDto = authTransformer.formToRequestOtpDto(data);
    mutate(dto, {
      onSuccess: (response: RequestOtpResponseDto) => onRequested(data.email, response.cooldownSeconds),
      onError: (error) => {
        setError('root', { message: getErrorMessage(error) });
      },
    });
  };

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
      {errors.root && <p className="rounded-md bg-error px-3 py-2 text-sm text-error-foreground">{errors.root.message}</p>}

      <div className="flex flex-col gap-2">
        <Label htmlFor="email">Email</Label>
        <Input {...register('email')} type="email" id="email" placeholder="researcher@uni-wuerzburg.de" />
        {errors.email && <p className="text-sm text-error-foreground">{errors.email.message}</p>}
      </div>

      <Button type="submit" className="w-full bg-jmu-blue-800 hover:bg-jmu-blue-800/90" disabled={isPending}>
        {isPending ? 'Sending code...' : 'Send login code'}
      </Button>
    </form>
  );
}

function CodeStep({
  email,
  initialCooldown,
  onChangeEmail,
  redirectTo,
}: {
  email: string;
  initialCooldown: number;
  onChangeEmail: () => void;
  /** the page the user was sent here from - where logging in returns them */
  redirectTo: string | null;
}) {
  const navigate = useNavigate();
  const { mutate, isPending } = useVerifyOtp();
  const { mutate: resend, isPending: isResending } = useRequestOtp();
  const [cooldown, setCooldown] = useState(initialCooldown);
  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<VerifyOtpFormData>({
    resolver: zodResolver(verifyOtpFormSchema),
    defaultValues: authTransformer.getInitialVerifyOtpFormValues(),
  });

  useEffect(() => {
    const timer = setInterval(() => setCooldown((seconds) => Math.max(0, seconds - 1)), 1000);
    return () => clearInterval(timer);
  }, []);

  const handleResend = () => {
    resend(
      { email },
      {
        onSuccess: (response: RequestOtpResponseDto) => {
          toast.success('Code resent — check your inbox.');
          setCooldown(response.cooldownSeconds);
        },
        onError: (error) => {
          toast.error(getErrorMessage(error));
        },
      },
    );
  };

  const onSubmit = (data: VerifyOtpFormData) => {
    const dto = authTransformer.formToVerifyOtpDto(email, data);
    mutate(dto, {
      onSuccess: (user) => {
        // an incomplete profile still goes first - it's needed before anything else
        navigate(user.firstName && user.lastName ? (redirectTo ?? ROUTES.home) : ROUTES.profile, { replace: true });
      },
      onError: (error) => {
        setError('root', { message: getErrorMessage(error) });
      },
    });
  };

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit(onSubmit)} noValidate>
      {errors.root && <p className="rounded-md bg-error px-3 py-2 text-sm text-error-foreground">{errors.root.message}</p>}

      <p className="text-sm text-slate-500">
        Code sent to <span className="font-medium text-slate-900">{email}</span>.{' '}
        <Button type="button" variant="link" onClick={onChangeEmail} className="h-auto p-0 font-semibold text-jmu-blue-800">
          Change email
        </Button>
      </p>

      <div className="flex flex-col gap-2">
        <Label htmlFor="code">Login code</Label>
        <Input {...register('code')} inputMode="numeric" id="code" placeholder="123456" maxLength={6} />
        {errors.code && <p className="text-sm text-error-foreground">{errors.code.message}</p>}
      </div>

      <Button type="submit" className="w-full bg-jmu-blue-800 hover:bg-jmu-blue-800/90" disabled={isPending}>
        {isPending ? 'Verifying...' : 'Verify and sign in'}
      </Button>

      <Button
        type="button"
        variant="link"
        onClick={handleResend}
        disabled={isResending || cooldown > 0}
        className="h-auto w-full p-0 text-sm font-semibold text-jmu-blue-800"
      >
        {isResending ? 'Resending...' : cooldown > 0 ? `Resend code in ${cooldown}s` : 'Resend code'}
      </Button>
    </form>
  );
}
/*
    Login Page is holding state of the current step of the login process (email = null | set).
    It starts with the email step (email = null), where the user can request a login code.
    Once the code is requested (email = set), it moves to the code verification step, where the user can enter the received code to log in.
 */
export default function LoginPage() {
  const [requested, setRequested] = useState<{ email: string; cooldownSeconds: number } | null>(null);
  const [searchParams] = useSearchParams();
  const redirectTo = safeRedirect(searchParams.get('redirect'));
  const sessionExpired = searchParams.get('reason') === 'expired';

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col items-center justify-center">
      <img src="/icons/Icon-S-dark.svg" alt="" />
      <h1 className="mt-4 text-2xl font-semibold text-slate-900">JMU Component Repository</h1>
      <p className="mt-1 text-slate-500">Sign in to your account</p>

      {sessionExpired && (
        <p className="mt-4 w-full rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
          Your session has expired. Log in again to continue where you left off.
        </p>
      )}

      <Card className="mt-6 w-full shadow-lg">
        <CardContent className="pt-6">
          {requested === null ? (
            <EmailStep onRequested={(email: string, cooldownSeconds: number) => { setRequested({email: email, cooldownSeconds: cooldownSeconds})}} />
          ) : (
            <CodeStep
              email={requested.email}
              initialCooldown={requested.cooldownSeconds}
              onChangeEmail={() => setRequested(null)}
              redirectTo={redirectTo}
            />
          )}
        </CardContent>
      </Card>

      <p className="mt-6 text-sm text-slate-500">We'll email you a one-time code — no password needed.</p>
    </div>
  );
}