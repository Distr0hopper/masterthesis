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
 * and render the same UploadMetadataFields.
 */
export const uploadMetadataSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  domains: z.array(z.string()).min(1, 'At least one domain is required'),
  description: descriptionSchema,
});

export type UploadMetadataFormData = z.infer<typeof uploadMetadataSchema>;

/** field name -> first validation message, for rendering inline errors */
export type UploadDetailsErrors = Partial<Record<keyof UploadMetadataFormData, string>>;

/**
 * Validate the metadata of a new upload. Returns the parsed data on success, or the
 * per-field errors to render. Every upload gates its final "Create"/"Save" on this - the
 * source itself is guaranteed by the flow, since step 2 needs a successful read.
 */
export function validateUploadMetadata(input: {
  name: string;
  domains: string[];
  description: string;
}): { data: UploadMetadataFormData; errors: null } | { data: null; errors: UploadDetailsErrors } {
  const result = uploadMetadataSchema.safeParse({ ...input, description: input.description || undefined });
  if (result.success) return { data: result.data, errors: null };

  const errors: UploadDetailsErrors = {};
  for (const issue of result.error.issues) {
    const field = issue.path[0] as keyof UploadDetailsErrors;
    if (field && !errors[field]) errors[field] = issue.message;
  }
  return { data: null, errors };
}
