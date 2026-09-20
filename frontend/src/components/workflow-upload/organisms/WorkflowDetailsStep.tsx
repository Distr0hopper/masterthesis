import { AlertTriangle } from 'lucide-react';
import { Input } from '@/components/ui/input.tsx';
import { Textarea } from '@/components/ui/textarea.tsx';
import { FileDropzone } from '@/components/common/FileDropzone';
import { FormField } from '@/components/common/FormField';
import { DomainMultiSelect } from '../common/DomainMultiSelect';
import type { UploadWorkflowFormErrors } from '@/api/workflows';

interface WorkflowDetailsStepProps {
  file: File | null;
  onFileChange: (file: File | null) => void;
  name: string;
  onNameChange: (value: string) => void;
  domains: string[];
  onDomainsChange: (value: string[]) => void;
  description: string;
  onDescriptionChange: (value: string) => void;
  errors: UploadWorkflowFormErrors;
  /** problems found by the parse that make this upload unsaveable as-is */
  blockingIssues: string[];
  parseError?: string;
}

/**
 * Name/domains/description are asked for here, next to the file - the same one-form
 * shape as the component upload's ManualUploadForm, rather than making the user parse
 * first and fill the metadata in afterwards.
 */
export function WorkflowDetailsStep({
  file,
  onFileChange,
  name,
  onNameChange,
  domains,
  onDomainsChange,
  description,
  onDescriptionChange,
  errors,
  blockingIssues,
  parseError,
}: WorkflowDetailsStepProps) {
  return (
    <div className="flex flex-col gap-6">
      {parseError && <p className="rounded-md bg-error px-3 py-2 text-sm text-error-foreground">{parseError}</p>}

      {blockingIssues.map((issue) => (
        <div key={issue} className="flex items-start gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{issue}</span>
        </div>
      ))}

      <FileDropzone
        value={file}
        onChange={onFileChange}
        accept=".zip,.cwl"
        label="Workflow File"
        helperText="A .zip archive or a bare .cwl file, or click to browse"
        error={errors.workflowFile}
      />

      <FormField htmlFor="workflow-name" label="Workflow Name" error={errors.name}>
        <Input
          id="workflow-name"
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          placeholder="e.g. thin-and-aggregate"
        />
      </FormField>

      <DomainMultiSelect value={domains} onChange={onDomainsChange} error={errors.domains} />

      <FormField htmlFor="workflow-description" label="Description" optional error={errors.description}>
        <Textarea
          id="workflow-description"
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
          placeholder="Brief description..."
          rows={4}
        />
      </FormField>
    </div>
  );
}
