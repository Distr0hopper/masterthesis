import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button.tsx';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { UploadStepper } from '@/components/common/UploadStepper';
import { UploadDetailsStep } from '@/components/common/UploadDetailsStep';
import { ComponentConfigStep } from '@/components/workflow-upload/organisms/ComponentConfigStep';
import { SaveWorkflowStep } from '@/components/workflow-upload/organisms/SaveWorkflowStep';
import { useComponentConfigs } from '@/components/workflow-upload/lib/useComponentConfigs';
import { useCreateWorkflow, useParseWorkflow, type ParseWorkflowResponseDto } from '@/api/workflows';
import { validateUploadDetails, type UploadDetailsErrors } from '@/api/schema';
import { getErrorMessage } from '@/lib/errors';
import { ROUTES } from '@/lib/routes';
import { stripUploadExtension } from '@/lib/filename';

const STEPS = [
  { id: 1, label: 'Workflow' },
  { id: 2, label: 'Components' },
  { id: 3, label: 'Save' },
];

export default function WorkflowUploadPage() {
  const navigate = useNavigate();
  const parseMutation = useParseWorkflow();
  const createMutation = useCreateWorkflow();

  const [step, setStep] = useState(1);
  const [furthest, setFurthest] = useState(1);
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState('');
  const [domains, setDomains] = useState<string[]>([]);
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<UploadDetailsErrors>({});
  // until the user types a name themselves, the filename (and then the CWL's own label:)
  // may fill it in for them - after that it is theirs and nothing overwrites it
  const nameTouched = useRef(false);

  const parsed = parseMutation.data;
  const previews = parsed?.componentPreviews ?? [];
  const configs = useComponentConfigs(previews);

  const goTo = (next: number) => {
    setStep(next);
    setFurthest((prev) => Math.max(prev, next));
  };

  const handleNameChange = (value: string) => {
    nameTouched.current = true;
    setName(value);
  };

  const handleFile = (selected: File | null) => {
    setFile(selected);
    parseMutation.reset();
    createMutation.reset();
    setErrors({});
    setStep(1);
    setFurthest(1);
    if (selected && !nameTouched.current) setName(stripUploadExtension(selected.name));
  };

  // every one of these makes the upload unsaveable as-is, so they block the whole flow
  const blockingIssues: string[] = [];
  if (parsed?.missingExternalRefs.length) {
    blockingIssues.push(
      `Missing referenced file(s) in the archive: ${parsed.missingExternalRefs.join(', ')}. Fix the archive and try again.`,
    );
  }
  if (parsed && !parsed.isZip && parsed.externalRefs.length > 0) {
    blockingIssues.push(
      `This .cwl file references step file(s) it doesn't contain: ${parsed.externalRefs.join(', ')}. Upload a .zip archive with them instead.`,
    );
  }
  if (parsed && parsed.componentPreviews.length === 0) {
    blockingIssues.push('No components could be read from this file.');
  }

  const handleContinueFromDetails = () => {
    const { data, errors: fieldErrors } = validateUploadDetails({ name, domains, file, description });
    if (!data) {
      setErrors(fieldErrors);
      return;
    }
    setErrors({});

    // already parsed this exact file and it was fine - don't re-upload it just to go forward
    if (parsed && blockingIssues.length === 0) {
      goTo(2);
      return;
    }

    parseMutation.mutate(data.file, {
      onSuccess: (response: ParseWorkflowResponseDto) => {
        if (!nameTouched.current && response.workflowName) setName(response.workflowName);
        configs.reset(response.componentPreviews);
        const hasBlockers =
          response.missingExternalRefs.length > 0 ||
          (!response.isZip && response.externalRefs.length > 0) ||
          response.componentPreviews.length === 0;
        if (!hasBlockers) goTo(2);
      },
    });
  };

  const canSave = configs.isComplete && blockingIssues.length === 0;

  const handleSave = () => {
    if (!file || !parsed || !canSave) return;
    createMutation.mutate(
      {
        file,
        dto: { name, domains, description: description || null, componentConfigs: configs.toDtos() },
      },
      {
        onSuccess: (created) => {
          toast.success(`${created.name} created`);
          navigate(ROUTES.workflowDetail(created.id));
        },
      },
    );
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Upload Workflow</h1>
      <p className="mt-1 text-slate-500">
        Upload a .zip archive (with a pipeline CWL file and the step CWL files it references), or a single
        self-contained .cwl file with its steps embedded inline. Every step is configured as a component
        before the workflow is saved.
      </p>

      <UploadStepper steps={STEPS} current={step} furthest={furthest} onSelect={goTo} />

      {step === 1 && (
        <Card className="mt-6">
          <CardContent className="pt-6">
            <UploadDetailsStep
              file={file}
              onFileChange={handleFile}
              accept=".zip,.cwl"
              fileLabel="Workflow File"
              fileHelperText="A .zip archive or a bare .cwl file, or click to browse"
              name={name}
              onNameChange={handleNameChange}
              nameLabel="Workflow Name"
              namePlaceholder="e.g. thin-and-aggregate"
              domains={domains}
              onDomainsChange={setDomains}
              description={description}
              onDescriptionChange={setDescription}
              errors={errors}
              issues={blockingIssues}
              error={
                parseMutation.error
                  ? getErrorMessage(parseMutation.error, 'Could not parse this file.')
                  : undefined
              }
            />
          </CardContent>
        </Card>
      )}

      {step === 2 && parsed && (
        <ComponentConfigStep
          parsed={parsed}
          previews={previews}
          configs={configs.configs}
          errors={configs.errors}
          onChange={configs.update}
          onApplyDomainsToAll={configs.applyDomainsToAll}
          onNameConflictChange={configs.setNameConflict}
        />
      )}

      {step === 3 && (
        <SaveWorkflowStep
          name={name}
          domains={domains}
          description={description}
          previews={previews}
          configs={configs.configs}
        />
      )}

      {createMutation.error && (
        <p className="mt-4 rounded-md bg-error px-3 py-2 text-sm text-error-foreground">
          {getErrorMessage(createMutation.error, 'Could not save this workflow.')}
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
            onClick={handleContinueFromDetails}
            disabled={parseMutation.isPending}
            className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
          >
            {parseMutation.isPending ? 'Reading file...' : 'Continue'}
          </Button>
        )}
        {step === 2 && (
          <Button
            onClick={() => goTo(3)}
            disabled={!configs.isComplete}
            className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
          >
            Continue
          </Button>
        )}
        {step === 3 && (
          <Button
            onClick={handleSave}
            disabled={!canSave || createMutation.isPending}
            className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
          >
            {createMutation.isPending ? 'Saving...' : 'Save Workflow'}
          </Button>
        )}
        {step === 2 && !configs.isComplete && (
          <span className="text-sm text-slate-500">Resolve the highlighted components to continue.</span>
        )}
      </div>
    </div>
  );
}
