import { useEffect, useId, type ReactNode } from 'react';
import { Input } from '@/components/ui/input.tsx';
import { Label } from '@/components/ui/label.tsx';
import { Textarea } from '@/components/ui/textarea.tsx';
import { FormField } from '@/components/common/FormField';
import { DomainBadges } from '@/components/common/DomainBadges';
import { DomainMultiSelect } from '@/components/common/DomainMultiSelect';
import type { UploadDetailsErrors } from '@/api/schema';

interface UploadMetadataFieldsProps {
  name: string;
  onNameChange: (value: string) => void;
  nameLabel: string;
  namePlaceholder?: string;
  /** shown but not editable - e.g. a new version keeps its lineage's name */
  nameReadOnly?: boolean;
  nameNotice?: ReactNode;
  domains: string[];
  onDomainsChange: (value: string[]) => void;
  domainsReadOnly?: boolean;
  description: string;
  onDescriptionChange: (value: string) => void;
  descriptionPlaceholder?: string;
  errors: UploadDetailsErrors;
}

const FIELDS = ['name', 'domains', 'description'] as const;

/**
 * Name + domains + description of a new upload - identical for components (from a file
 * or GitHub) and workflows, and shown next to the preview so it can be edited in review.
 *
 * Scrolls the first invalid field into view whenever new validation errors come in -
 * on the review steps it can sit far above a long preview.
 */
export function UploadMetadataFields({
  name,
  onNameChange,
  nameLabel,
  namePlaceholder,
  nameReadOnly = false,
  nameNotice,
  domains,
  onDomainsChange,
  domainsReadOnly = false,
  description,
  onDescriptionChange,
  descriptionPlaceholder,
  errors,
}: UploadMetadataFieldsProps) {
  const id = useId();
  const fieldId = (field: keyof UploadDetailsErrors) => `${id}-${field}`;

  useEffect(() => {
    const invalid = FIELDS.find((field) => errors[field]);
    if (invalid) document.getElementById(`${id}-${invalid}`)?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }, [errors, id]);

  return (
    <div className="flex flex-col gap-6">
      <FormField htmlFor={fieldId('name')} label={nameLabel} error={errors.name}>
        <Input
          id={fieldId('name')}
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          placeholder={namePlaceholder}
          readOnly={nameReadOnly}
          disabled={nameReadOnly}
        />
      </FormField>

      {nameNotice}

      <div id={fieldId('domains')}>
        {domainsReadOnly ? (
          <div className="flex flex-col gap-2">
            <Label>Domains</Label>
            <div className="flex flex-wrap gap-2">
              <DomainBadges domains={domains} />
            </div>
          </div>
        ) : (
          <DomainMultiSelect value={domains} onChange={onDomainsChange} error={errors.domains} />
        )}
      </div>

      <FormField
        htmlFor={fieldId('description')}
        label="Description"
        optional
        error={errors.description}
      >
        <Textarea
          id={fieldId('description')}
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
          placeholder={descriptionPlaceholder}
          rows={4}
        />
      </FormField>
    </div>
  );
}
