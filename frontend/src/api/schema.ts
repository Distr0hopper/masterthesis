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
 * The metadata describing every new upload - components (from a file or GitHub) and
 * workflows ask for exactly the same things, so they validate against the same rules
 * and render the same UploadDetailsStep.
 */
export const uploadMetadataSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  domains: z.array(z.string()).min(1, 'At least one domain is required'),
  description: descriptionSchema,
});

/** The first step of a file upload: the file plus the metadata that describes it. */
export const uploadDetailsFormSchema = uploadMetadataSchema.extend({
  file: z.instanceof(File, { message: 'A file is required' }),
});

export type UploadMetadataFormData = z.infer<typeof uploadMetadataSchema>;
export type UploadDetailsFormData = z.infer<typeof uploadDetailsFormSchema>;

/** field name -> first validation message, for rendering inline errors */
export type UploadDetailsErrors = Partial<Record<keyof UploadDetailsFormData, string>>;

type ValidationResult<T> = { data: T; errors: null } | { data: null; errors: UploadDetailsErrors };

function validate<T>(schema: z.ZodType<T>, input: unknown): ValidationResult<T> {
  const result = schema.safeParse(input);
  if (result.success) return { data: result.data, errors: null };

  const errors: UploadDetailsErrors = {};
  for (const issue of result.error.issues) {
    const field = issue.path[0] as keyof UploadDetailsErrors;
    if (field && !errors[field]) errors[field] = issue.message;
  }
  return { data: null, errors };
}

/**
 * Validate the shared upload-details fields. Returns the parsed data on success, or the
 * per-field errors to render. Both file-upload pages gate their "Continue" on this.
 */
export function validateUploadDetails(input: {
  name: string;
  domains: string[];
  file: File | null;
  description: string;
}): ValidationResult<UploadDetailsFormData> {
  return validate(uploadDetailsFormSchema, { ...input, description: input.description || undefined });
}

/** Like {@link validateUploadDetails}, for uploads whose source isn't a file (GitHub packaging). */
export function validateUploadMetadata(input: {
  name: string;
  domains: string[];
  description: string;
}): ValidationResult<UploadMetadataFormData> {
  return validate(uploadMetadataSchema, { ...input, description: input.description || undefined });
}
