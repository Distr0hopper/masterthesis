import { z } from 'zod';

// mirrors the backend's MAX_DESCRIPTION_LENGTH (app/domain/models/workflow.py)
export const MAX_DESCRIPTION_LENGTH = 2000;

const descriptionSchema = z
  .string()
  .max(MAX_DESCRIPTION_LENGTH, `Description must be at most ${MAX_DESCRIPTION_LENGTH} characters`)
  .optional();

export const uploadWorkflowFormSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  domains: z.array(z.string()).min(1, 'Select at least one domain'),
  zipFile: z.instanceof(File, { message: 'Workflow zip archive is required' }),
  description: descriptionSchema,
});

export type UploadWorkflowFormData = z.infer<typeof uploadWorkflowFormSchema>;
