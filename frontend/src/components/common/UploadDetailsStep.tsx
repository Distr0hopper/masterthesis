import type { ReactNode } from 'react';
import { AlertTriangle, Info } from 'lucide-react';
import { Input } from '@/components/ui/input.tsx';
import { Label } from '@/components/ui/label.tsx';
import { Textarea } from '@/components/ui/textarea.tsx';
import { FormField } from '@/components/common/FormField';
import { DomainBadges } from '@/components/common/DomainBadges';
import { DomainMultiSelect } from '@/components/common/DomainMultiSelect';
import type { UploadDetailsErrors } from '@/api/schema';

interface UploadDetailsStepProps {
  /** where the upload comes from - a FileDropzone, or the GitHub repo-URL field */
  source: ReactNode;
  /** info box under the source - defaults to the ontology/EDAM explanation */
  hint?: ReactNode;
  name: string;
  onNameChange: (value: string) => void;
  nameLabel: string;
  namePlaceholder?: string;
  /** shown but not editable - e.g. a new version keeps its lineage's name */
  nameReadOnly?: boolean;
  domains: string[];
  onDomainsChange: (value: string[]) => void;
  domainsReadOnly?: boolean;
  description: string;
  onDescriptionChange: (value: string) => void;
  descriptionPlaceholder?: string;
  errors: UploadDetailsErrors;
  nameNotice?: ReactNode;
  issues?: string[];
  error?: string;
}

const ONTOLOGY_HINT = (
  <>
    Parameter formats are resolved against the ontology referenced in the CWL&apos;s{' '}
    <code className="text-xs">$schemas</code>. Currently only the <strong>EDAM</strong> ontology (
    <code className="text-xs">http://edamontology.org/</code>) is supported. The workflow builder can only verify that
    two components fit together when both declare an EDAM format - ports without a format, or with a format from another
    ontology, are kept but not labelled and show up as unverified connections.
  </>
);

/**
 * Source + name + domains + description - the opening step of every upload: a component
 * from a file or from GitHub, and a workflow.
 */
export function UploadDetailsStep({
  source,
  hint = ONTOLOGY_HINT,
  name,
  onNameChange,
  nameLabel,
  namePlaceholder,
  nameReadOnly = false,
  domains,
  onDomainsChange,
  domainsReadOnly = false,
  description,
  onDescriptionChange,
  descriptionPlaceholder = "Filled in from the file's doc: field once it's read - or write your own",
  errors,
  nameNotice,
  issues = [],
  error,
}: UploadDetailsStepProps) {
  return (
    <div className="flex flex-col gap-6">
      {error && <p className="rounded-md bg-error px-3 py-2 text-sm text-error-foreground">{error}</p>}

      {issues.map((issue) => (
        <div key={issue} className="flex items-start gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{issue}</span>
        </div>
      ))}

      {source}

      <div className="flex items-start gap-2 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">
        <Info className="mt-0.5 h-4 w-4 shrink-0" />
        <span>{hint}</span>
      </div>

      <FormField htmlFor="upload-name" label={nameLabel} error={errors.name}>
        <Input
          id="upload-name"
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          placeholder={namePlaceholder}
          readOnly={nameReadOnly}
          disabled={nameReadOnly}
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
        <DomainMultiSelect value={domains} onChange={onDomainsChange} error={errors.domains} />
      )}

      <FormField htmlFor="upload-description" label="Description" optional error={errors.description}>
        <Textarea
          id="upload-description"
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
          placeholder={descriptionPlaceholder}
          rows={4}
        />
      </FormField>
    </div>
  );
}
