import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
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
  initialFormatLabelDraft,
  toFormatLabelDtos,
  withFormatLabels,
  type FormatLabelDraft,
  useComponentNameAvailability,
} from '@/api/components';
import {
  toolTransformer,
  useAddManualVersion,
  useParseTool,
  useUploadTool,
  type ToolDetailDisplayModel,
  type ToolDetailDto,
} from '@/api/tools';
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
  onSuccess?: (created: ToolDetailDto) => void;
  parent?: ToolDetailDisplayModel;
}

export function ManualUploadWizard({ onSuccess, parent }: ManualUploadWizardProps) {
  const navigate = useNavigate();
  const parseMutation = useParseTool();
  const uploadMutation = useUploadTool();
  const addVersionMutation = useAddManualVersion();
  const {
    isPending: isCreating,
    error: createError,
    reset: resetCreate,
  } = parent ? addVersionMutation : uploadMutation;
  const wizard = useUploadWizard();
  const { form, prefill } = useUploadMetadataForm(parent && { name: parent.name, domains: parent.domains });

  const [file, setFile] = useState<File | null>(null);
  const carriedLabels = parent ? initialFormatLabelDraft([...parent.inputs, ...parent.outputs]) : {};
  const [formatLabels, setFormatLabels] = useState<FormatLabelDraft>(carriedLabels);

  const { name, domains, description } = useWatch({ control: form.control });
  const debouncedName = useDebouncedValue(parent ? '' : (name ?? ''));
  const { data: availability } = useComponentNameAvailability(debouncedName);

  const taken = !parent && availability?.available === false;
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
    setFormatLabels(carriedLabels);
    wizard.backToSource();
    if (selected) {
      if (!parent) prefill({ name: stripUploadExtension(selected.name) });
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
    if (parent) {
      addVersionMutation.mutate(
        {
          id: parent.id,
          file,
          dto: {
            description: values.description || null,
            formatLabels: toFormatLabelDtos(parsed.parameters, formatLabels),
          },
        },
        {
          onSuccess: (created) => {
            toast.success(`${created.name} v${created.version} created`);
            if (onSuccess) onSuccess(created);
            else navigate(ROUTES.toolDetail(created.id));
          },
        },
      );
      return;
    }
    uploadMutation.mutate(
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
            {takenBy.canAddVersion ? (
              <>
                — rename yours, or{' '}
                <Link to={ROUTES.toolNewVersion(takenBy.id)} className="font-medium underline">
                  add a new version to it
                </Link>{' '}
                instead.
              </>
            ) : (
              '— choose a different name.'
            )}
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
        { name, domains, description, ...(parent && { version: parent.version + 1 }) },
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
            title={parent ? `New version of ${parent.name}` : 'New tool'}
            locked={!!parent}
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
              {isCreating ? 'Creating...' : parent ? 'Create Version' : 'Create Tool'}
            </Button>
          )}
        </div>
      </div>
    </FormProvider>
  );
}
