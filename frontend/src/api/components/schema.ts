import { z } from 'zod';
import { descriptionSchema } from '@/api/schema';

export const updateComponentFormSchema = z.object({
  description: descriptionSchema,
  domains: z.array(z.string()).min(1, 'At least one domain is required').optional(),
});

export type UpdateComponentFormData = z.infer<typeof updateComponentFormSchema>;
