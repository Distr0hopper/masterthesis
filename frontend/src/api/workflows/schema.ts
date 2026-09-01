import { z } from 'zod';
import { descriptionSchema } from '@/api/schema';

export const uploadWorkflowFormSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  domains: z.array(z.string()).min(1, 'Select at least one domain'),
  zipFile: z.instanceof(File, { message: 'Workflow zip archive is required' }),
  description: descriptionSchema,
});

export type UploadWorkflowFormData = z.infer<typeof uploadWorkflowFormSchema>;

export const updateWorkflowDescriptionFormSchema = z.object({
  description: descriptionSchema,
});

export type UpdateWorkflowDescriptionFormData = z.infer<typeof updateWorkflowDescriptionFormSchema>;
