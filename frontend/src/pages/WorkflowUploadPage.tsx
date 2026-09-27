import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FormProvider, useWatch } from 'react-hook-form';
import { toast } from 'sonner';
import { AlertTriangle, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button.tsx';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { UploadStepper } from '@/components/common/UploadStepper';
import { UploadSourceStep } from '@/components/common/UploadSourceStep';
import { useUploadWizard } from '@/components/common/useUploadWizard';
import { useUploadMetadataForm } from '@/components/common/useUploadMetadataForm';
import { FileDropzone } from '@/components/common/FileDropzone';
import { ComponentConfigStep } from '@/components/workflow-upload/organisms/ComponentConfigStep';
import { useComponentConfigs } from '@/components/workflow-upload/lib/useComponentConfigs';
import {
  useCreateWorkflow,
  useParseWorkflow,
  useWorkflowNameAvailability,
  type ParseWorkflowResponseDto,
} from '@/api/workflows';
import type { UploadMetadataFormData } from '@/api/schema';
import { getErrorMessage } from '@/lib/errors';
import { ROUTES } from '@/lib/routes';
import { stripUploadExtension } from '@/lib/filename';
import { useDebouncedValue } from '@/lib/useDebouncedValue';

const STEPS = [
  { id: 1, label: 'Source' },
  { id: 2, label: 'Configure & save' },
];

/** Problems in the uploaded file that make it impossible to continue - shown on the source step. */
function blockersOf(parsed: ParseWorkflowResponseDto | undefined): string[] {
  if (!parsed) return [];
  const blockers: string[] = [];
  if (parsed.missingExternalRefs.length) {
    blockers.push(
      `Missing referenced file(s) in the archive: ${parsed.missingExternalRefs.join(', ')}. Fix the archive and try again.`,
    );
  }
  if (parsed.missingImports.length) {
    blockers.push(
      `Imported file(s) missing from the archive: ${parsed.missingImports.join(', ')}. The workflow references these type definitions and cannot run without them.`,
    );
  }
  if (!parsed.isZip && parsed.externalRefs.length > 0) {
    blockers.push(
      `This .cwl file references step file(s) it doesn't contain: ${parsed.externalRefs.join(', ')}. Upload a .zip archive with them instead.`,
    );
  }
  if (parsed.componentPreviews.length === 0) {
    blockers.push('No components could be read from this file.');
  }
  return blockers;
}

export default function WorkflowUploadPage() {
  const navigate = useNavigate();
  const parseMutation = useParseWorkflow();
  const createMutation = useCreateWorkflow();

  const wizard = useUploadWizard();
  const { form, prefill } = useUploadMetadataForm();
  const [file, setFile] = useState<File | null>(null);

  const name = useWatch({ control: form.control, name: 'name' });
  const debouncedName = useDebouncedValue(name);
  const { data: nameAvailability } = useWorkflowNameAvailability(debouncedName);

  const nameTaken = nameAvailability?.available === false;
  const nameTakenBy = nameTaken ? nameAvailability?.existing : null;

  const parsed = parseMutation.data;
  const previews = parsed?.componentPreviews ?? [];
  const configs = useComponentConfigs(previews);

  /** Pre-fill what the parse extracted - only fields the user hasn't edited themselves. */
  const applyParsed = (response: ParseWorkflowResponseDto) => {
    prefill({ name: response.workflowName || undefined, description: response.description ?? '' });
    configs.reset(response.componentPreviews);
  };

  const readFile = (selected: File) => {
    parseMutation.mutate(selected, {
      onSuccess: (response) => {
        applyParsed(response);
        if (blockersOf(response).length === 0) wizard.goTo(2);
      },
    });
  };

  const handleFile = (selected: File | null) => {
    setFile(selected);
    parseMutation.reset();
    createMutation.reset();
    form.clearErrors();
    wizard.backToSource();
    if (selected) {
      prefill({ name: stripUploadExtension(selected.name) });
      readFile(selected);
    }
  };

  const blockingIssues = blockersOf(parsed);

  // back on the source step without changing it - or retrying a read that failed
  const handleContinue = () => {
    if (parsed && blockingIssues.length === 0) wizard.goTo(2);
    else if (file && !parsed) readFile(file);
  };

  const canSave = configs.isComplete && blockingIssues.length === 0 && !nameTaken;

  const handleSave = (values: UploadMetadataFormData) => {
    if (!file || !parsed || !canSave) return;
    createMutation.mutate(
      {
        file,
        dto: {
          name: values.name,
          domains: values.domains,
          description: values.description || null,
          componentConfigs: configs.toDtos(),
        },
      },
      {
        onSuccess: (created) => {
          toast.success(`${created.name} created`);
          navigate(ROUTES.workflowDetail(created.id));
        },
      },
    );
  };

  const nameNotice = nameTaken ? (
    // plain inline text, real spaces - see the note in ManualUploadWizard
    <div className="flex items-start gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <span>
        {nameTakenBy ? (
          <>
            A workflow named{' '}
            <a
              href={ROUTES.workflowDetail(nameTakenBy.id)}
              target="_blank"
              rel="noreferrer"
              title="Open it in a new tab"
              className="inline-flex items-center gap-1 font-mono font-semibold hover:underline"
            >
              {nameTakenBy.name}
              <ExternalLink className="h-3.5 w-3.5" />
            </a>{' '}
            already exists — choose a different name.
          </>
        ) : (
          'That name is already taken — choose a different name.'
        )}
      </span>
    </div>
  ) : undefined;

  return (
    <FormProvider {...form}>
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Upload Workflow</h1>
        <p className="mt-1 text-slate-500">
          Upload a .zip archive (with a pipeline CWL file and the step CWL files it references), or a single
          self-contained .cwl file with its steps embedded inline. Every step is configured as a component before the
          workflow is saved.
        </p>

        <UploadStepper steps={STEPS} current={wizard.step} furthest={wizard.furthest} onSelect={wizard.goTo} />

        {wizard.step === 1 && (
          <Card className="mt-6">
            <CardContent className="pt-6">
              <UploadSourceStep
                source={
                  <FileDropzone
                    value={file}
                    onChange={handleFile}
                    accept=".zip,.cwl"
                    label="Workflow File"
                    helperText="A .zip archive or a bare .cwl file, or click to browse"
                  />
                }
                isReading={parseMutation.isPending}
                readingLabel="Reading file..."
                issues={blockingIssues}
                error={
                  parseMutation.error ? getErrorMessage(parseMutation.error, 'Could not parse this file.') : undefined
                }
              />
            </CardContent>
          </Card>
        )}

        {wizard.step === 2 && parsed && (
          <ComponentConfigStep
            parsed={parsed}
            workflowNameNotice={nameNotice}
            previews={previews}
            configs={configs.configs}
            errors={configs.errors}
            onChange={configs.update}
            onApplyDomainsToAll={configs.applyDomainsToAll}
            onNameConflictChange={configs.setNameConflict}
          />
        )}

        {createMutation.error && (
          <p className="mt-4 rounded-md bg-error px-3 py-2 text-sm text-error-foreground">
            {getErrorMessage(createMutation.error, 'Could not save this workflow.')}
          </p>
        )}

        <div className="mt-6 flex items-center gap-2">
          {wizard.step > 1 && (
            <Button variant="outline" onClick={() => wizard.goTo(wizard.step - 1)}>
              Back
            </Button>
          )}
          {wizard.step === 1 && (
            <Button
              onClick={handleContinue}
              disabled={parseMutation.isPending || !file || blockingIssues.length > 0}
              className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
            >
              {parseMutation.isPending ? 'Reading file...' : 'Continue'}
            </Button>
          )}
          {wizard.step === 2 && (
            <Button
              onClick={form.handleSubmit(handleSave)}
              disabled={!canSave || createMutation.isPending}
              className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
            >
              {createMutation.isPending ? 'Saving...' : 'Save Workflow'}
            </Button>
          )}
          {wizard.step === 2 && !configs.isComplete && (
            <span className="text-sm text-slate-500">Resolve the highlighted components to continue.</span>
          )}
        </div>
      </div>
    </FormProvider>
  );
}
