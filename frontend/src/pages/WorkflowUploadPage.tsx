import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { AlertTriangle, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button.tsx';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { UploadStepper } from '@/components/common/UploadStepper';
import { UploadSourceStep } from '@/components/common/UploadSourceStep';
import { UploadMetadataFields } from '@/components/common/UploadMetadataFields';
import { FileDropzone } from '@/components/common/FileDropzone';
import { ComponentConfigStep } from '@/components/workflow-upload/organisms/ComponentConfigStep';
import { useComponentConfigs } from '@/components/workflow-upload/lib/useComponentConfigs';
import {
  useCreateWorkflow,
  useParseWorkflow,
  useWorkflowNameAvailability,
  type ParseWorkflowResponseDto,
} from '@/api/workflows';
import { validateUploadMetadata, type UploadDetailsErrors } from '@/api/schema';
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

  const [step, setStep] = useState(1);
  const [furthest, setFurthest] = useState(1);
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState('');
  const [domains, setDomains] = useState<string[]>([]);
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<UploadDetailsErrors>({});

  const nameTouched = useRef(false);
  const descriptionTouched = useRef(false);

  const debouncedName = useDebouncedValue(name);
  const { data: nameAvailability } = useWorkflowNameAvailability(debouncedName);

  const nameTaken = nameAvailability?.available === false;
  const nameTakenBy = nameTaken ? nameAvailability?.existing : null;

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

  const handleDescriptionChange = (value: string) => {
    descriptionTouched.current = true;
    setDescription(value);
  };

  /** Pre-fill what the parse extracted - only fields the user hasn't edited themselves. */
  const applyParsed = (response: ParseWorkflowResponseDto) => {
    if (!nameTouched.current && response.workflowName) setName(response.workflowName);
    if (!descriptionTouched.current) setDescription(response.description ?? '');
    configs.reset(response.componentPreviews);
  };

  const readFile = (selected: File) => {
    parseMutation.mutate(selected, {
      onSuccess: (response) => {
        applyParsed(response);
        if (blockersOf(response).length === 0) goTo(2);
      },
    });
  };

  const handleFile = (selected: File | null) => {
    setFile(selected);
    parseMutation.reset();
    createMutation.reset();
    setErrors({});
    setStep(1);
    setFurthest(1);
    if (selected && !nameTouched.current) setName(stripUploadExtension(selected.name));
    if (selected) readFile(selected);
  };

  const blockingIssues = blockersOf(parsed);

  // back on the source step without changing it - or retrying a read that failed
  const handleContinue = () => {
    if (parsed && blockingIssues.length === 0) goTo(2);
    else if (file && !parsed) readFile(file);
  };

  const canSave = configs.isComplete && blockingIssues.length === 0 && !nameTaken;

  const handleSave = () => {
    if (!file || !parsed || !canSave) return;
    const { data, errors: fieldErrors } = validateUploadMetadata({ name, domains, description });
    if (!data) {
      setErrors(fieldErrors);
      return;
    }
    setErrors({});
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
            already exists \u2014 choose a different name.
          </>
        ) : (
          'That name is already taken \u2014 choose a different name.'
        )}
      </span>
    </div>
  ) : undefined;

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
          workflowDetails={
            <UploadMetadataFields
              name={name}
              onNameChange={handleNameChange}
              nameLabel="Workflow Name"
              namePlaceholder="e.g. thin-and-aggregate"
              nameNotice={nameNotice}
              domains={domains}
              onDomainsChange={setDomains}
              description={description}
              onDescriptionChange={handleDescriptionChange}
              descriptionPlaceholder="Taken from the workflow's doc: field - or write your own"
              errors={errors}
            />
          }
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
        {step > 1 && (
          <Button variant="outline" onClick={() => goTo(step - 1)}>
            Back
          </Button>
        )}
        {step === 1 && (
          <Button
            onClick={handleContinue}
            disabled={parseMutation.isPending || !file || blockingIssues.length > 0}
            className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
          >
            {parseMutation.isPending ? 'Reading file...' : 'Continue'}
          </Button>
        )}
        {step === 2 && (
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
