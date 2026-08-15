import { z } from 'zod';

// mirrors the backend's MAX_DESCRIPTION_LENGTH (each entity - Component, Workflow -
// defines its own copy of this constant on the backend, but the frontend validation
// shape is identical, so it's shared here rather than duplicated per feature)
export const MAX_DESCRIPTION_LENGTH = 2000;

export const descriptionSchema = z
  .string()
  .max(MAX_DESCRIPTION_LENGTH, `Description must be at most ${MAX_DESCRIPTION_LENGTH} characters`)
  .optional();
