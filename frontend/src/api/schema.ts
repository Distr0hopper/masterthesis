import { z } from 'zod';

// mirrors the backend's MAX_DESCRIPTION_LENGTH (each entity - Component, Workflow -
// defines its own copy of this constant on the backend, but the frontend validation
// shape is identical, so it's shared here rather than duplicated per feature)
export const MAX_DESCRIPTION_LENGTH = 2000;

export const descriptionSchema = z
  .string()
  .max(MAX_DESCRIPTION_LENGTH, `Description must be at most ${MAX_DESCRIPTION_LENGTH} characters`)
  .optional();

/**
 * The first step of every upload: the file plus the metadata that describes it.
 * Components and workflows ask for exactly the same things, so they validate against
 * exactly the same schema and render the same UploadDetailsStep.
 */
export const uploadDetailsFormSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  domains: z.array(z.string()).min(1, 'At least one domain is required'),
  file: z.instanceof(File, { message: 'A file is required' }),
  description: descriptionSchema,
});

export type UploadDetailsFormData = z.infer<typeof uploadDetailsFormSchema>;

/** field name -> first validation message, for rendering inline errors */
export type UploadDetailsErrors = Partial<Record<keyof UploadDetailsFormData, string>>;

/**
 * Validate the shared upload-details fields. Returns the parsed data on success, or the
 * per-field errors to render. Both upload pages gate their "Continue" on this.
 */
export function validateUploadDetails(input: {
  name: string;
  domains: string[];
  file: File | null;
  description: string;
}): { data: UploadDetailsFormData; errors: null } | { data: null; errors: UploadDetailsErrors } {
  const result = uploadDetailsFormSchema.safeParse({
    name: input.name,
    domains: input.domains,
    file: input.file,
    description: input.description || undefined,
  });
  if (result.success) return { data: result.data, errors: null };

  const errors: UploadDetailsErrors = {};
  for (const issue of result.error.issues) {
    const field = issue.path[0] as keyof UploadDetailsErrors;
    if (field && !errors[field]) errors[field] = issue.message;
  }
  return { data: null, errors };
}
