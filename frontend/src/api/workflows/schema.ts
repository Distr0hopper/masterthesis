import { z } from 'zod';
import { descriptionSchema } from '@/api/schema';

/**
 * Step 1 of the workflow upload - deliberately the same shape as
 * uploadComponentFormSchema, so both uploads ask for the file and its metadata in one
 * go. `domains` is a list (a workflow spans several) where a component has exactly one.
 */
export const uploadWorkflowFormSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  domains: z.array(z.string()).min(1, 'At least one domain is required'),
  workflowFile: z.instanceof(File, { message: 'Workflow file is required' }),
  description: descriptionSchema,
});

export type UploadWorkflowFormData = z.infer<typeof uploadWorkflowFormSchema>;

/** field name -> first validation message, for rendering inline errors */
export type UploadWorkflowFormErrors = Partial<Record<keyof UploadWorkflowFormData, string>>;

export const updateWorkflowDescriptionFormSchema = z.object({
  description: descriptionSchema,
});

export type UpdateWorkflowDescriptionFormData = z.infer<typeof updateWorkflowDescriptionFormSchema>;
