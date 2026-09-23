import type { ReactNode } from 'react';
import { AlertTriangle, Info } from 'lucide-react';
import { Input } from '@/components/ui/input.tsx';
import { Textarea } from '@/components/ui/textarea.tsx';
import { FileDropzone } from '@/components/common/FileDropzone';
import { FormField } from '@/components/common/FormField';
import { DomainMultiSelect } from '@/components/common/DomainMultiSelect';
import type { UploadDetailsErrors } from '@/api/schema';

interface UploadDetailsStepProps {
  file: File | null;
  onFileChange: (file: File | null) => void;
  /** e.g. ".cwl" or ".zip,.cwl" */
  accept: string;
  fileLabel: string;
  fileHelperText?: string;
  name: string;
  onNameChange: (value: string) => void;
  nameLabel: string;
  namePlaceholder?: string;
  domains: string[];
  onDomainsChange: (value: string[]) => void;
  description: string;
  onDescriptionChange: (value: string) => void;
  errors: UploadDetailsErrors;
  nameNotice?: ReactNode;
  issues?: string[];
  error?: string;
}

/**
 * File + name + domains + description - the opening step of both the component and the
 * workflow upload.
 */
export function UploadDetailsStep({
  file,
  onFileChange,
  accept,
  fileLabel,
  fileHelperText,
  name,
  onNameChange,
  nameLabel,
  namePlaceholder,
  domains,
  onDomainsChange,
  description,
  onDescriptionChange,
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

      <FileDropzone
        value={file}
        onChange={onFileChange}
        accept={accept}
        label={fileLabel}
        helperText={fileHelperText}
        error={errors.file}
      />

      <div className="flex items-start gap-2 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-600">
        <Info className="mt-0.5 h-4 w-4 shrink-0" />
        <span>
          Parameter formats are resolved against the ontology referenced in the CWL&apos;s{' '}
          <code className="text-xs">$schemas</code>. Currently only the <strong>EDAM</strong> ontology (
          <code className="text-xs">http://edamontology.org/</code>) is supported. The workflow builder can only verify
          that two components fit together when both declare an EDAM format - ports without a format, or with a format
          from another ontology, are kept but not labelled and show up as unverified connections.
        </span>
      </div>

      <FormField htmlFor="upload-name" label={nameLabel} error={errors.name}>
        <Input
          id="upload-name"
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          placeholder={namePlaceholder}
        />
      </FormField>

      {nameNotice}

      <DomainMultiSelect value={domains} onChange={onDomainsChange} error={errors.domains} />

      <FormField htmlFor="upload-description" label="Description" optional error={errors.description}>
        <Textarea
          id="upload-description"
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
          placeholder="Brief description..."
          rows={4}
        />
      </FormField>
    </div>
  );
}
