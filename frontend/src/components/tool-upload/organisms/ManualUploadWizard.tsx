import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FormProvider, useWatch } from 'react-hook-form';
import { AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button.tsx';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { UploadSourceStep } from '@/components/common/UploadSourceStep';
import { FileDropzone } from '@/components/common/FileDropzone';
import { UploadStepper } from '@/components/common/UploadStepper';
import { ComponentLink } from '@/components/common/ComponentLink';
import { useUploadWizard } from '@/components/common/useUploadWizard';
import { useUploadMetadataForm } from '@/components/common/useUploadMetadataForm';
import { ToolReviewStep } from './ToolReviewStep';
import {
  toFormatLabelDtos,
  withFormatLabels,
  type FormatLabelDraft,
  useComponentNameAvailability,
} from '@/api/components';
import { toolTransformer, useParseTool, useUploadTool, type ToolDetailDto } from '@/api/tools';
import type { UploadMetadataFormData } from '@/api/schema';
import { useDebouncedValue } from '@/lib/useDebouncedValue';
import { getErrorMessage } from '@/lib/errors';
import { ROUTES } from '@/lib/routes';
import { stripUploadExtension } from '@/lib/filename';

const STEPS = [
  { id: 1, label: 'Source' },
  { id: 2, label: 'Details & review' },
];

interface ManualUploadWizardProps {
  // when provided, replaces the default post-upload navigation - used to embed this in
  // contexts like the workflow step picker, where navigating away would abandon
  // whatever page it was opened from
  onSuccess?: (created: ToolDetailDto) => void;
}

export function ManualUploadWizard({ onSuccess }: ManualUploadWizardProps) {
  const navigate = useNavigate();
  const parseMutation = useParseTool();
  const { mutate: upload, isPending: isCreating, error: createError, reset: resetCreate } = useUploadTool();
  const wizard = useUploadWizard();
  const { form, prefill } = useUploadMetadataForm();

  const [file, setFile] = useState<File | null>(null);
  const [formatLabels, setFormatLabels] = useState<FormatLabelDraft>({});

  const { name, domains, description } = useWatch({ control: form.control });
  const debouncedName = useDebouncedValue(name ?? '');
  const { data: availability } = useComponentNameAvailability(debouncedName);

  const taken = availability?.available === false;
  const takenBy = taken ? availability?.existing : null;

  const parsed = parseMutation.data;

  const readFile = (selected: File) => {
    parseMutation.mutate(selected, {
      onSuccess: (response) => {
        prefill({ description: response.description ?? '' });
        wizard.goTo(2);
      },
    });
  };

  const handleFile = (selected: File | null) => {
    setFile(selected);
    parseMutation.reset();
    resetCreate();
    form.clearErrors();
    setFormatLabels({});
    wizard.backToSource();
    if (selected) {
      prefill({ name: stripUploadExtension(selected.name) });
      readFile(selected);
    }
  };

  // back on the source step without changing it - or retrying a read that failed
  const handleContinue = () => {
    if (parsed) wizard.goTo(2);
    else if (file) readFile(file);
  };

  const handleCreate = (values: UploadMetadataFormData) => {
    if (!file || !parsed || taken) return;
    upload(
      {
        file,
        dto: {
          name: values.name,
          domains: values.domains,
          description: values.description || null,
          formatLabels: toFormatLabelDtos(parsed.parameters, formatLabels),
        },
      },
      {
        onSuccess: (created) => {
          toast.success(`${created.name} created`);
          if (onSuccess) onSuccess(created);
          else navigate(ROUTES.toolDetail(created.id));
        },
      },
    );
  };

  const nameNotice = taken ? (
    <div className="flex items-start gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <span>
        {takenBy ? (
          <>
            This name is already taken by{' '}
            <ComponentLink
              componentId={takenBy.id}
              kind={takenBy.kind}
              name={takenBy.name}
              version={takenBy.version}
              className="inline-flex"
            />{' '}
            {takenBy.canAddVersion
              ? '— rename yours, or add a new version to it instead.'
              : '— choose a different name.'}
          </>
        ) : (
          'This name is already taken — choose a different name.'
        )}
      </span>
    </div>
  ) : undefined;

  const previewModel = parsed
    ? toolTransformer.toPreviewDisplayModel(
        {
          ...parsed,
          parameters: withFormatLabels(parsed.parameters, formatLabels),
        },
        { name, domains, description },
      )
    : null;

  return (
    <FormProvider {...form}>
      <div>
        <UploadStepper steps={STEPS} current={wizard.step} furthest={wizard.furthest} onSelect={wizard.goTo} />

        {wizard.step === 1 && (
          <Card className="mt-6">
            <CardContent className="pt-6">
              <UploadSourceStep
                source={<FileDropzone value={file} onChange={handleFile} accept=".cwl" label="CWL File" />}
                isReading={parseMutation.isPending}
                readingLabel="Reading file..."
                error={
                  parseMutation.error ? getErrorMessage(parseMutation.error, 'Could not read this file.') : undefined
                }
              />
            </CardContent>
          </Card>
        )}

        {wizard.step === 2 && parsed && previewModel && (
          <ToolReviewStep
            title="New tool"
            nameNotice={nameNotice}
            descriptionPlaceholder="Taken from the file's doc: field - or write your own"
            previewModel={previewModel}
            parameters={parsed.parameters}
            formatLabels={formatLabels}
            onFormatLabelsChange={setFormatLabels}
          />
        )}

        {createError && (
          <p className="mt-4 rounded-md bg-error px-3 py-2 text-sm text-error-foreground">
            {getErrorMessage(createError, 'Could not create this tool.')}
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
              disabled={parseMutation.isPending || !file}
              className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
            >
              {parseMutation.isPending ? 'Reading file...' : 'Continue'}
            </Button>
          )}
          {wizard.step === 2 && (
            <Button
              onClick={form.handleSubmit(handleCreate)}
              disabled={isCreating || taken}
              className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
            >
              {isCreating ? 'Creating...' : 'Create Tool'}
            </Button>
          )}
        </div>
      </div>
    </FormProvider>
  );
}
