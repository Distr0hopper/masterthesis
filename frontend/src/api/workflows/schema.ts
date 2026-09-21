import { z } from 'zod';
import { descriptionSchema } from '@/api/schema';

export const updateWorkflowDescriptionFormSchema = z.object({
  description: descriptionSchema,
});

export type UpdateWorkflowDescriptionFormData = z.infer<typeof updateWorkflowDescriptionFormSchema>;
