import { z } from 'zod';
import { descriptionSchema } from '@/api/schema';

export const packageComponentFormSchema = z.object({
  repoUrl: z.url('Invalid repository URL'),
  domains: z.array(z.string()).min(1, 'At least one domain is required'),
  description: descriptionSchema,
});

export type PackageComponentFormData = z.infer<typeof packageComponentFormSchema>;

export const updateComponentFormSchema = z.object({
  description: descriptionSchema,
  domains: z.array(z.string()).min(1, 'At least one domain is required').optional(),
});

export type UpdateComponentFormData = z.infer<typeof updateComponentFormSchema>;