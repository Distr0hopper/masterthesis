import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { emptyUploadMetadata, uploadMetadataSchema, type UploadMetadataFormData } from '@/api/schema';

/**
 * The name/domains/description form of an upload wizard. The wizard provides it via
 * FormProvider; UploadMetadataFields renders it wherever it sits in the steps.
 */
export function useUploadMetadataForm() {
  const form = useForm<UploadMetadataFormData>({
    resolver: zodResolver(uploadMetadataSchema),
    defaultValues: emptyUploadMetadata,
  });
  // read during render so react-hook-form tracks dirtiness - prefill() depends on it
  const { dirtyFields } = form.formState;

  /**
   * Fill in values read from the source (file name, CWL doc:, README, ...) - only into
   * fields the user hasn't edited. setValue without shouldDirty keeps them untouched, so
   * the next source can fill them again.
   */
  const prefill = (values: Partial<Pick<UploadMetadataFormData, 'name' | 'description'>>) => {
    for (const [field, value] of Object.entries(values) as [keyof typeof values, string | undefined][]) {
      if (value !== undefined && !dirtyFields[field]) form.setValue(field, value);
    }
  };

  return { form, prefill };
}
