import { z } from 'zod';

export const requestOtpFormSchema = z.object({
  email: z.email('Invalid email address'),
});

export type RequestOtpFormData = z.infer<typeof requestOtpFormSchema>;

export const verifyOtpFormSchema = z.object({
  code: z
    .string()
    .length(6, 'Enter the 6-digit code')
    .regex(/^\d{6}$/, 'Code must be numeric'),
});

export type VerifyOtpFormData = z.infer<typeof verifyOtpFormSchema>;