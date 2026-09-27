import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AxiosError } from 'axios';
import { AlertTriangle, Info } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button.tsx';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Input } from '@/components/ui/input.tsx';
import { FormField } from '@/components/common/FormField';
import { UploadSourceStep } from '@/components/common/UploadSourceStep';
import { UploadMetadataFields } from '@/components/common/UploadMetadataFields';
import { UploadStepper } from '@/components/common/UploadStepper';
import { ComponentLink } from '@/components/common/ComponentLink';
import { ComponentReviewStep } from '@/components/component-upload/organisms/ComponentReviewStep';
import {
  ComponentSource,
  componentTransformer,
  initialFormatLabelDraft,
  repoUrlSchema,
  toFormatLabelDtos,
  useComponentNameAvailability,
  usePackageComponent,
  usePackagePreview,
  withFormatLabels,
  type FormatLabelDraft,
  type PackagePreviewDto,
} from '@/api/components';
import { validateUploadMetadata, type UploadDetailsErrors } from '@/api/schema';
import { useDebouncedValue } from '@/lib/useDebouncedValue';
import { getErrorMessage } from '@/lib/errors';
import { ROUTES } from '@/lib/routes';

const STEPS = [
  { id: 1, label: 'Repository' },
  { id: 2, label: 'Details & review' },
];

/** Why a fetched repo can't be packaged at all - shown on the source step, blocks continuing. */
function sourceIssuesOf(preview: PackagePreviewDto | undefined): string[] {
  if (preview?.alreadyPackaged) {
    return [`Already up to date - commit ${preview.commitSha.slice(0, 7)} is the latest packaged version.`];
  }
  if (preview?.existing && !preview.existing.canAddVersion) {
    return ['This repository is already packaged, and only its owner can add new versions.'];
  }
  return [];
}

const PACKAGING_HINT = (
  <>
    The repository&apos;s <code className="text-xs">appspec.json</code> is turned into a CWL CommandLineTool and
    Dockerfile. MoveApps apps declare no ontology formats, so every File port can be labelled by hand in the review
    step.
  </>
);

/**
 * Package a MoveApps GitHub repo as a component - the same source -> details & review
 * flow as ManualUploadWizard, with the repo URL as the source. A repo that's already
 * packaged becomes a new version of its component instead (name and domains locked).
 */
export function PackageFromGitHubWizard() {
  const navigate = useNavigate();
  const previewMutation = usePackagePreview();
  const { mutate: packageComponent, isPending: isCreating, error: createError, reset: resetCreate } =
    usePackageComponent();

  const [step, setStep] = useState(1);
  const [furthest, setFurthest] = useState(1);
  const [repoUrl, setRepoUrl] = useState('');
  const [repoUrlError, setRepoUrlError] = useState<string>();
  const [name, setName] = useState('');
  const [domains, setDomains] = useState<string[]>([]);
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<UploadDetailsErrors>({});
  const [formatLabels, setFormatLabels] = useState<FormatLabelDraft>({});
  const nameTouched = useRef(false);
  const descriptionTouched = useRef(false);

  const preview = previewMutation.data;
  const existing = preview?.existing ?? null;
  const isNewVersion = existing !== null;

  // a new version keeps its lineage's name, so there's nothing to check
  const debouncedName = useDebouncedValue(isNewVersion ? '' : name);
  const { data: availability } = useComponentNameAvailability(debouncedName);
  const taken = !isNewVersion && availability?.available === false;

  const sourceIssues = sourceIssuesOf(preview);

  const goTo = (next: number) => {
    setStep(next);
    setFurthest((prev) => Math.max(prev, next));
  };

  const applyPreview = (response: PackagePreviewDto) => {
    if (response.existing) {
      setName(response.existing.name);
      setDomains(response.existing.domains);
    } else if (!nameTouched.current) {
      setName(response.repoName);
    }
    if (!descriptionTouched.current) setDescription(response.description ?? '');
    // for a new version: the labels carried over from the previous one
    setFormatLabels(initialFormatLabelDraft(response.parameters));
  };

  const fetchPreview = () => {
    const result = repoUrlSchema.safeParse(repoUrl.trim());
    if (!result.success) {
      setRepoUrlError(result.error.issues[0]?.message);
      return;
    }
    setRepoUrlError(undefined);
    resetCreate();
    previewMutation.mutate(result.data, {
      onSuccess: (response) => {
        applyPreview(response);
        if (sourceIssuesOf(response).length > 0) setStep(1);
        else goTo(2);
      },
    });
  };

  const handleRepoUrlChange = (value: string) => {
    setRepoUrl(value);
    // a different repo invalidates everything read from the previous one
    if (previewMutation.data || previewMutation.error) {
      previewMutation.reset();
      resetCreate();
      setFormatLabels({});
      setErrors({});
      setStep(1);
      setFurthest(1);
    }
  };

  // back on the source step without changing it - or retrying a fetch that failed
  const handleContinue = () => {
    if (preview && sourceIssues.length === 0) goTo(2);
    else if (!preview) fetchPreview();
  };

  const handleCreate = () => {
    if (!preview || sourceIssues.length > 0 || taken) return;
    const { data, errors: fieldErrors } = validateUploadMetadata({ name, domains, description });
    if (!data) {
      setErrors(fieldErrors);
      return;
    }
    setErrors({});
    packageComponent(
      {
        repoUrl: preview.repoUrl,
        name: isNewVersion ? null : name,
        domains,
        description: description || null,
        formatLabels: toFormatLabelDtos(preview.parameters, formatLabels),
        expectedCommitSha: preview.commitSha,
      },
      {
        onSuccess: (created) => {
          toast.success(isNewVersion ? `${created.name} v${created.version} packaged` : `${created.name} packaged`);
          navigate(ROUTES.componentDetail(created.id));
        },
      },
    );
  };

  // 409 covers "the repo moved on since this preview" - re-reading it is the way out
  const createConflict = createError instanceof AxiosError && createError.response?.status === 409;

  const nameNotice = existing ? (
    <div className="flex items-start gap-2 rounded-md bg-jmu-blue-50 px-3 py-2 text-sm text-jmu-blue-900">
      <Info className="mt-0.5 h-4 w-4 shrink-0" />
      <span>
        This repository is already packaged as{' '}
        <ComponentLink componentId={existing.id} name={existing.name} version={existing.version} className="inline-flex" />
        {' — '}this creates version {existing.version + 1}.
      </span>
    </div>
  ) : taken ? (
    <div className="flex items-start gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <span>
        {availability?.existing ? (
          <>
            This name is already taken by{' '}
            <ComponentLink
              componentId={availability.existing.id}
              name={availability.existing.name}
              version={availability.existing.version}
              className="inline-flex"
            />{' '}
            {'— choose a different name.'}
          </>
        ) : (
          'This name is already taken — choose a different name.'
        )}
      </span>
    </div>
  ) : undefined;

  const previewModel = preview
    ? componentTransformer.toPreviewDisplayModel(
        { ...preview, parameters: withFormatLabels(preview.parameters, formatLabels) },
        {
          name,
          domains,
          description,
          source: ComponentSource.AUTOMATED_PACKAGING,
          repoUrl: preview.repoUrl,
          version: existing ? existing.version + 1 : 1,
        },
      )
    : null;

  const repoSource = (
    <FormField htmlFor="package-repo-url" label="Repository URL" error={repoUrlError}>
      <div className="flex gap-2">
        <Input
          id="package-repo-url"
          value={repoUrl}
          onChange={(e) => handleRepoUrlChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              fetchPreview();
            }
          }}
          placeholder="https://github.com/movestore/Remove_Outliers"
        />
        <Button
          type="button"
          variant="outline"
          onClick={() => fetchPreview()}
          disabled={previewMutation.isPending || !repoUrl.trim()}
        >
          {previewMutation.isPending ? 'Packaging...' : preview ? 'Fetch again' : 'Fetch'}
        </Button>
      </div>
    </FormField>
  );

  return (
    <div>
      <UploadStepper steps={STEPS} current={step} furthest={furthest} onSelect={goTo} />

      {step === 1 && (
        <Card className="mt-6">
          <CardContent className="pt-6">
            <UploadSourceStep
              source={repoSource}
              hint={PACKAGING_HINT}
              isReading={previewMutation.isPending}
              readingLabel="Packaging the repository - this takes a few seconds..."
              issues={sourceIssues}
              error={
                previewMutation.error
                  ? getErrorMessage(previewMutation.error, 'Could not package this repository.')
                  : undefined
              }
            />
          </CardContent>
        </Card>
      )}

      {step === 2 && preview && previewModel && (
        <ComponentReviewStep
          title={existing ? `New version of ${existing.name}` : 'New component'}
          details={
            <UploadMetadataFields
              name={name}
              onNameChange={(value) => {
                nameTouched.current = true;
                setName(value);
              }}
              nameLabel="Component Name"
              nameReadOnly={isNewVersion}
              nameNotice={nameNotice}
              domains={domains}
              onDomainsChange={setDomains}
              domainsReadOnly={isNewVersion}
              description={description}
              onDescriptionChange={(value) => {
                descriptionTouched.current = true;
                setDescription(value);
              }}
              descriptionPlaceholder="Taken from the repository's README - or write your own"
              errors={errors}
            />
          }
          previewModel={previewModel}
          parameters={preview.parameters}
          formatLabels={formatLabels}
          onFormatLabelsChange={setFormatLabels}
        />
      )}

      {createError && (
        <div className="mt-4 flex flex-wrap items-center gap-3 rounded-md bg-error px-3 py-2 text-sm text-error-foreground">
          <span>{getErrorMessage(createError, 'Could not package this component.')}</span>
          {createConflict && (
            <Button size="sm" variant="outline" onClick={fetchPreview}>
              Fetch again
            </Button>
          )}
        </div>
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
            disabled={previewMutation.isPending || !repoUrl.trim() || sourceIssues.length > 0}
            className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
          >
            {previewMutation.isPending ? 'Packaging...' : 'Continue'}
          </Button>
        )}
        {step === 2 && (
          <Button
            onClick={handleCreate}
            disabled={isCreating || taken}
            className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
          >
            {isCreating ? 'Packaging...' : isNewVersion ? 'Create Version' : 'Create Component'}
          </Button>
        )}
      </div>
    </div>
  );
}
