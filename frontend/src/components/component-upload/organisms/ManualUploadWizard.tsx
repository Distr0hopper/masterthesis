import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button.tsx';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { UploadDetailsStep } from '@/components/common/UploadDetailsStep';
import { UploadStepper } from '@/components/common/UploadStepper';
import { ComponentLink } from '@/components/common/ComponentLink';
import { DomainBadges } from '@/components/common/DomainBadges';
import { ComponentTabs } from '@/components/component-detail/organisms/ComponentTabs';
import { FormatLabelFields } from '@/components/common/FormatLabelFields';
import {
  componentTransformer,
  toFormatLabelDtos,
  withFormatLabels,
  type FormatLabelDraft,
  useComponentNameAvailability,
  useParseComponent,
  useUploadComponent,
  type ComponentDetailDto,
  type ComponentPreviewDto,
} from '@/api/components';
import { validateUploadDetails, type UploadDetailsErrors } from '@/api/schema';
import { useDebouncedValue } from '@/lib/useDebouncedValue';
import { getErrorMessage } from '@/lib/errors';
import { ROUTES } from '@/lib/routes';
import { stripUploadExtension } from '@/lib/filename';

const STEPS = [
  { id: 1, label: 'Component' },
  { id: 2, label: 'Review' },
];

interface ManualUploadWizardProps {
  // when provided, replaces the default post-upload navigation - used to embed this in
  // contexts like the workflow step picker, where navigating away would abandon
  // whatever page it was opened from
  onSuccess?: (created: ComponentDetailDto) => void;
}

export function ManualUploadWizard({ onSuccess }: ManualUploadWizardProps) {
  const navigate = useNavigate();
  const parseMutation = useParseComponent();
  const { mutate: upload, isPending: isCreating, error: createError, reset: resetCreate } = useUploadComponent();

  const [step, setStep] = useState(1);
  const [furthest, setFurthest] = useState(1);
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState('');
  const [domains, setDomains] = useState<string[]>([]);
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<UploadDetailsErrors>({});
  const [formatLabels, setFormatLabels] = useState<FormatLabelDraft>({});
  const nameTouched = useRef(false);
  const descriptionTouched = useRef(false);

  const debouncedName = useDebouncedValue(name);
  const { data: availability } = useComponentNameAvailability(debouncedName);

  const taken = availability?.available === false;
  const takenBy = taken ? availability?.existing : null;

  const parsed = parseMutation.data;

  const goTo = (next: number) => {
    setStep(next);
    setFurthest((prev) => Math.max(prev, next));
  };

  const applyParsed = (response: ComponentPreviewDto) => {
    if (!descriptionTouched.current) setDescription(response.description ?? '');
  };

  const handleFile = (selected: File | null) => {
    setFile(selected);
    parseMutation.reset();
    resetCreate();
    setErrors({});
    setFormatLabels({});
    setStep(1);
    setFurthest(1);
    if (selected && !nameTouched.current) setName(stripUploadExtension(selected.name));
    if (selected) parseMutation.mutate(selected, { onSuccess: applyParsed });
  };

  const handleContinue = () => {
    const { data, errors: fieldErrors } = validateUploadDetails({ name, domains, file, description });
    if (!data) {
      setErrors(fieldErrors);
      return;
    }
    setErrors({});
    if (taken) return;

    if (parsed) {
      goTo(2);
      return;
    }
    parseMutation.mutate(data.file, {
      onSuccess: (response) => {
        applyParsed(response);
        goTo(2);
      },
    });
  };

  const handleCreate = () => {
    if (!file || taken) return;
    upload(
      {
        file,
        dto: {
          name,
          domains,
          description: description || null,
          formatLabels: parsed ? toFormatLabelDtos(parsed.parameters, formatLabels) : [],
        },
      },
      {
        onSuccess: (created) => {
          toast.success(`${created.name} created`);
          if (onSuccess) onSuccess(created);
          else navigate(ROUTES.componentDetail(created.id));
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
              name={takenBy.name}
              version={takenBy.version}
              className="inline-flex"
            />{' '}
            {takenBy.canAddVersion
              ? '\u2014 rename yours, or add a new version to it instead.'
              : '\u2014 choose a different name.'}
          </>
        ) : (
          'This name is already taken \u2014 choose a different name.'
        )}
      </span>
    </div>
  ) : undefined;

  const previewModel = parsed
    ? componentTransformer.toPreviewDisplayModel(
        { ...parsed, parameters: withFormatLabels(parsed.parameters, formatLabels) },
        { name, domains, description },
      )
    : null;

  return (
    <div>
      <UploadStepper steps={STEPS} current={step} furthest={furthest} onSelect={goTo} />

      {step === 1 && (
        <Card className="mt-6">
          <CardContent className="pt-6">
            <UploadDetailsStep
              file={file}
              onFileChange={handleFile}
              accept=".cwl"
              fileLabel="CWL File"
              name={name}
              onNameChange={(value) => {
                nameTouched.current = true;
                setName(value);
              }}
              nameLabel="Component Name"
              namePlaceholder="e.g. remove-outliers"
              domains={domains}
              onDomainsChange={setDomains}
              description={description}
              onDescriptionChange={(value) => {
                descriptionTouched.current = true;
                setDescription(value);
              }}
              errors={errors}
              nameNotice={nameNotice}
              error={
                parseMutation.error ? getErrorMessage(parseMutation.error, 'Could not read this file.') : undefined
              }
            />
          </CardContent>
        </Card>
      )}

      {step === 2 && previewModel && (
        <>
          <Card className="mt-6">
            <CardContent className="flex flex-col gap-3 pt-6">
              <p className="text-sm font-medium text-slate-900">This component will be created</p>
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-semibold text-slate-900">{name}</span>
                <Badge variant="secondary">v1</Badge>
                <DomainBadges domains={domains} />
              </div>
              {previewModel.description && <p className="text-sm text-slate-500">{previewModel.description}</p>}
              <FormatLabelFields
                parameters={parsed!.parameters}
                value={formatLabels}
                onChange={setFormatLabels}
                idPrefix="upload"
              />
            </CardContent>
          </Card>
          <ComponentTabs model={previewModel} isPreview />
        </>
      )}

      {createError && (
        <p className="mt-4 rounded-md bg-error px-3 py-2 text-sm text-error-foreground">
          {getErrorMessage(createError, 'Could not create this component.')}
        </p>
      )}

      <div className="mt-6 flex items-center gap-2">
        {step > 1 && (
          <Button variant="outline" onClick={() => goTo(step - 1)}>
            Back
          </Button>
        )}
        {step === 1 && (
          <Button
            onClick={handleContinue}
            disabled={parseMutation.isPending || taken}
            className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
          >
            {parseMutation.isPending ? 'Reading file...' : 'Continue'}
          </Button>
        )}
        {step === 2 && (
          <Button
            onClick={handleCreate}
            disabled={isCreating || taken}
            className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
          >
            {isCreating ? 'Creating...' : 'Create Component'}
          </Button>
        )}
      </div>
    </div>
  );
}
