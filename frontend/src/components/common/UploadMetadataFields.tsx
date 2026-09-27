import { useId, type ReactNode } from 'react';
import { Controller, useFormContext, useWatch } from 'react-hook-form';
import { Input } from '@/components/ui/input.tsx';
import { Label } from '@/components/ui/label.tsx';
import { Textarea } from '@/components/ui/textarea.tsx';
import { FormField } from '@/components/common/FormField';
import { DomainBadges } from '@/components/common/DomainBadges';
import { DomainMultiSelect } from '@/components/common/DomainMultiSelect';
import type { UploadMetadataFormData } from '@/api/schema';

interface UploadMetadataFieldsProps {
  nameLabel: string;
  namePlaceholder?: string;
  /** shown but not editable - e.g. a new version keeps its lineage's name */
  nameReadOnly?: boolean;
  nameNotice?: ReactNode;
  domainsReadOnly?: boolean;
  descriptionPlaceholder?: string;
}

/**
 * Name + domains + description of a new upload - identical for components (from a file
 * or GitHub) and workflows, and shown next to the preview so it can be edited in review.
 *
 * Reads and writes the wizard's form (useUploadMetadataForm) from context, so wherever
 * it's rendered inside the wizard's FormProvider, nothing has to be passed down. On a
 * failed submit, react-hook-form focuses (and so scrolls to) the first invalid field.
 */
export function UploadMetadataFields({
  nameLabel,
  namePlaceholder,
  nameReadOnly = false,
  nameNotice,
  domainsReadOnly = false,
  descriptionPlaceholder,
}: UploadMetadataFieldsProps) {
  const id = useId();
  const {
    register,
    control,
    formState: { errors },
  } = useFormContext<UploadMetadataFormData>();
  const domains = useWatch({ control, name: 'domains' });

  return (
    <div className="flex flex-col gap-6">
      <FormField htmlFor={`${id}-name`} label={nameLabel} error={errors.name?.message}>
        {/* readOnly, not disabled - react-hook-form leaves disabled fields out of the submitted values */}
        <Input
          {...register('name')}
          id={`${id}-name`}
          placeholder={namePlaceholder}
          readOnly={nameReadOnly}
          className={nameReadOnly ? 'cursor-not-allowed opacity-50' : undefined}
        />
      </FormField>

      {nameNotice}

      {domainsReadOnly ? (
        <div className="flex flex-col gap-2">
          <Label>Domains</Label>
          <div className="flex flex-wrap gap-2">
            <DomainBadges domains={domains} />
          </div>
        </div>
      ) : (
        <Controller
          control={control}
          name="domains"
          render={({ field }) => (
            <DomainMultiSelect
              value={field.value}
              onChange={field.onChange}
              inputRef={field.ref}
              error={errors.domains?.message}
            />
          )}
        />
      )}

      <FormField htmlFor={`${id}-description`} label="Description" optional error={errors.description?.message}>
        <Textarea {...register('description')} id={`${id}-description`} placeholder={descriptionPlaceholder} rows={4} />
      </FormField>
    </div>
  );
}
