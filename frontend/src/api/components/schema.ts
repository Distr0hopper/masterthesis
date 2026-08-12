import { z } from 'zod';

// mirrors the backend's MAX_DESCRIPTION_LENGTH (app/domain/models/component.py)
export const MAX_DESCRIPTION_LENGTH = 2000;

const descriptionSchema = z
  .string()
  .max(MAX_DESCRIPTION_LENGTH, `Description must be at most ${MAX_DESCRIPTION_LENGTH} characters`)
  .optional();

export const uploadComponentFormSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  domain: z.string().min(1, 'Domain is required'),
  authorName: z.string().optional(),
  cwlFile: z.instanceof(File, { message: 'CWL file is required' }),
  description: descriptionSchema,
});

export type UploadComponentFormData = z.infer<typeof uploadComponentFormSchema>;

export const packageComponentFormSchema = z.object({
  repoUrl: z.url('Invalid repository URL'),
  domain: z.string().min(1, 'Domain is required'),
  description: descriptionSchema,
});

export type PackageComponentFormData = z.infer<typeof packageComponentFormSchema>;

export const updateComponentFormSchema = z.object({
  description: descriptionSchema,
  domain: z.string().min(1, 'Domain is required').optional(),
});

export type UpdateComponentFormData = z.infer<typeof updateComponentFormSchema>;