import { z } from 'zod';

export const updateProfileFormSchema = z.object({
  firstName: z.string().min(1, 'First name is required'),
  lastName: z.string().min(1, 'Last name is required'),
  affiliation: z.string().optional(),
});

export type UpdateProfileFormData = z.infer<typeof updateProfileFormSchema>;