import { z } from 'zod';

export const uploadComponentFormSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  domain: z.string().min(1, 'Domain is required'),
  authorName: z.string().optional(),
  cwlFile: z.instanceof(File, { message: 'CWL file is required' }),
  description: z.string().optional(),
});

export type UploadComponentFormData = z.infer<typeof uploadComponentFormSchema>;

export const packageComponentFormSchema = z.object({
  repoUrl: z.url('Invalid repository URL'),
  domain: z.string().min(1, 'Domain is required'),
  description: z.string().optional(),
});

export type PackageComponentFormData = z.infer<typeof packageComponentFormSchema>;

export const updateComponentFormSchema = z.object({
  description: z.string().optional(),
  domain: z.string().min(1, 'Domain is required').optional(),
});

export type UpdateComponentFormData = z.infer<typeof updateComponentFormSchema>;