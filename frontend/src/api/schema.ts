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
 * and render the same UploadMetadataFields (see useUploadMetadataForm).
 */
export const uploadMetadataSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  domains: z.array(z.string()).min(1, 'At least one domain is required'),
  description: descriptionSchema,
});

export type UploadMetadataFormData = z.infer<typeof uploadMetadataSchema>;

export const emptyUploadMetadata: UploadMetadataFormData = { name: '', domains: [], description: '' };
