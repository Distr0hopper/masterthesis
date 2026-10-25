import { useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { FormProvider, useWatch } from 'react-hook-form';
import { AxiosError } from 'axios';
import { AlertTriangle, Info } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button.tsx';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Input } from '@/components/ui/input.tsx';
import { FormField } from '@/components/common/FormField';
import { UploadSourceStep } from '@/components/common/UploadSourceStep';
import { UploadStepper } from '@/components/common/UploadStepper';
import { ComponentLink } from '@/components/common/ComponentLink';
import { useUploadMetadataForm } from '@/components/common/useUploadMetadataForm';
import { ToolReviewStep } from './ToolReviewStep';
import { sourceIssuesOf } from '../lib/sourceIssues';
import {
  ComponentSource,
  initialFormatLabelDraft,
  toFormatLabelDtos,
  useComponentNameAvailability,
  withFormatLabels,
  type FormatLabelDraft,
} from '@/api/components';
import {
  repoUrlSchema,
  toolTransformer,
  usePackagePreview,
  usePackageTool,
  type PackagePreviewDto,
} from '@/api/tools';
import type { UploadMetadataFormData } from '@/api/schema';
import { useDebouncedValue } from '@/lib/useDebouncedValue';
import { getErrorMessage } from '@/lib/errors';
import { ROUTES } from '@/lib/routes';

const STEPS = [
  { id: 1, label: 'Repository' },
  { id: 2, label: 'Details & review' },
];

const PACKAGING_HINT = (
  <>
    The repository&apos;s <code className="text-xs">appspec.json</code> is turned into a CWL CommandLineTool and
    Dockerfile. MoveApps apps declare no ontology formats, so every File port can be labelled by hand in the review
    step.
  </>
);

interface PackageFromGitHubWizardProps {
  /** the repo of the tool this packages a new version of - read right away and not editable */
  fixedRepoUrl?: string;
}

/**
 * Package a MoveApps GitHub repo as a tool - the same source -> details & review
 * flow as ManualUploadWizard, with the repo URL as the source. A repo that's already
 * packaged becomes a new version of its tool instead (name and domains locked).
 *
 * This part owns only the URL and the preview query. Everything read from a preview - the
 * form, the format labels, the step - lives in PackageWizardSteps, keyed by the preview:
 * a new preview mounts it fresh with its initial state taken from it, so no effect has to
 * copy the result over.
 */
export function PackageFromGitHubWizard({ fixedRepoUrl }: PackageFromGitHubWizardProps = {}) {
  const [repoUrl, setRepoUrl] = useState(fixedRepoUrl ?? '');
  const [repoUrlError, setRepoUrlError] = useState<string>();
  // the URL the preview is loaded for - set by the source step's button, and from the start for a given repo
  const [submittedUrl, setSubmittedUrl] = useState<string | null>(fixedRepoUrl ?? null);
  const previewQuery = usePackagePreview(submittedUrl);
  const preview = previewQuery.data;

  const fetchPreview = () => {
    const result = repoUrlSchema.safeParse(repoUrl.trim());
    if (!result.success) {
      setRepoUrlError(result.error.issues[0]?.message);
      return;
    }
    setRepoUrlError(undefined);
    if (result.data === submittedUrl) previewQuery.refetch();
    else setSubmittedUrl(result.data);
  };

  const handleRepoUrlChange = (value: string) => {
    setRepoUrl(value);
    // a different repo invalidates everything read from the previous one
    setSubmittedUrl(null);
  };

  // Enter submits like the step's one button - which knows whether that means reading or going on
  const repoSource = (onSubmit: () => void) => (
    <FormField htmlFor="package-repo-url" label="Repository URL" error={repoUrlError}>
      <Input
        id="package-repo-url"
        value={repoUrl}
        onChange={(e) => handleRepoUrlChange(e.target.value)}
        readOnly={fixedRepoUrl !== undefined}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            onSubmit();
          }
        }}
        placeholder="https://github.com/movestore/Remove_Outliers"
      />
    </FormField>
  );

  return (
    <PackageWizardSteps
      // the same repo at the same commit keeps what was typed; anything else starts over
      key={preview ? `${preview.repoUrl}@${preview.commitSha}#${preview.existing?.id ?? ''}:${preview.alreadyPackaged}` : 'none'}
      preview={preview}
      repoSource={repoSource}
      isReading={previewQuery.isFetching}
      // hidden while reading again, so a retry that fails the same way still shows as a fresh result
      readError={
        previewQuery.error && !previewQuery.isFetching
          ? getErrorMessage(previewQuery.error, 'Could not package this repository.')
          : undefined
      }
      canFetch={!!repoUrl.trim()}
      onFetch={fetchPreview}
    />
  );
}

interface PackageWizardStepsProps {
  preview: PackagePreviewDto | undefined;
  repoSource: (onSubmit: () => void) => ReactNode;
  isReading: boolean;
  readError: string | undefined;
  canFetch: boolean;
  onFetch: () => void;
}

/** The steps for one preview - mounted fresh for every new one, see PackageFromGitHubWizard. */
function PackageWizardSteps({ preview, repoSource, isReading, readError, canFetch, onFetch }: PackageWizardStepsProps) {
  const navigate = useNavigate();
  const { mutate: packageComponent, isPending: isCreating, error: createError } = usePackageTool();

  const existing = preview?.existing ?? null;
  const isNewVersion = existing !== null;
  const sourceIssues = sourceIssuesOf(preview);
  const reviewable = !!preview && sourceIssues.length === 0;

  // a preview that can be packaged opens on its review
  const [step, setStep] = useState(reviewable ? 2 : 1);
  const { form } = useUploadMetadataForm(
    preview && {
      // a new version keeps its lineage's name and domains - shown locked
      name: existing?.name ?? preview.repoName,
      domains: existing?.domains ?? [],
      description: preview.description ?? '',
    },
  );
  // for a new version: the labels carried over from the previous one
  const [formatLabels, setFormatLabels] = useState<FormatLabelDraft>(() =>
    preview ? initialFormatLabelDraft(preview.parameters) : {},
  );

  const { name, domains, description } = useWatch({ control: form.control });
  // a new version keeps its lineage's name, so there's nothing to check
  const debouncedName = useDebouncedValue(isNewVersion ? '' : (name ?? ''));
  const { data: availability } = useComponentNameAvailability(debouncedName);
  const taken = !isNewVersion && availability?.available === false;

  // the source step's one button: read the repo - first time, after a failure, or after a push
  // that may have cleared an issue - or, back on it with a reviewable preview, simply go on
  const handlePrimary = () => {
    if (reviewable) setStep(2);
    else onFetch();
  };
  const primaryLabel = isReading
    ? 'Packaging...'
    : readError
      ? 'Try again'
      : sourceIssues.length > 0
        ? 'Check again'
        : 'Continue';

  const handleCreate = (values: UploadMetadataFormData) => {
    if (!preview || !reviewable || taken) return;
    packageComponent(
      {
        repoUrl: preview.repoUrl,
        name: isNewVersion ? null : values.name,
        domains: values.domains,
        description: values.description || null,
        formatLabels: toFormatLabelDtos(preview.parameters, formatLabels),
        expectedCommitSha: preview.commitSha,
      },
      {
        onSuccess: (created) => {
          toast.success(isNewVersion ? `${created.name} v${created.version} packaged` : `${created.name} packaged`);
          navigate(ROUTES.toolDetail(created.id));
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
        <ComponentLink
          componentId={existing.id}
          kind={existing.kind}
          name={existing.name}
          version={existing.version}
          className="inline-flex"
        />
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
              kind={availability.existing.kind}
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
    ? toolTransformer.toPreviewDisplayModel(
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

  return (
    <FormProvider {...form}>
      <div>
        <UploadStepper steps={STEPS} current={step} furthest={reviewable ? 2 : 1} onSelect={setStep} />

        {step === 1 && (
          <Card className="mt-6">
            <CardContent className="pt-6">
              <UploadSourceStep
                source={repoSource(handlePrimary)}
                hint={PACKAGING_HINT}
                isReading={isReading}
                readingLabel="Packaging the repository - this takes a few seconds..."
                issues={sourceIssues}
                error={readError}
              />
            </CardContent>
          </Card>
        )}

        {step === 2 && preview && previewModel && (
          <ToolReviewStep
            title={existing ? `New version of ${existing.name}` : 'New tool'}
            locked={isNewVersion}
            nameNotice={nameNotice}
            descriptionPlaceholder="Taken from the repository's README - or write your own"
            previewModel={previewModel}
            parameters={preview.parameters}
            formatLabels={formatLabels}
            onFormatLabelsChange={setFormatLabels}
          />
        )}

        {createError && (
          <div className="mt-4 flex flex-wrap items-center gap-3 rounded-md bg-error px-3 py-2 text-sm text-error-foreground">
            <span>{getErrorMessage(createError, 'Could not package this tool.')}</span>
            {createConflict && (
              <Button size="sm" variant="outline" onClick={onFetch} disabled={isReading}>
                {isReading ? 'Packaging...' : 'Fetch again'}
              </Button>
            )}
          </div>
        )}

        <div className="mt-6 flex items-center gap-2">
          {step > 1 && (
            <Button variant="outline" onClick={() => setStep(step - 1)}>
              Back
            </Button>
          )}
          {step === 1 && (
            <Button
              onClick={handlePrimary}
              disabled={isReading || !canFetch}
              className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
            >
              {primaryLabel}
            </Button>
          )}
          {step === 2 && (
            <Button
              onClick={form.handleSubmit(handleCreate)}
              disabled={isCreating || taken}
              className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
            >
              {isCreating ? 'Packaging...' : isNewVersion ? 'Create Version' : 'Create Tool'}
            </Button>
          )}
        </div>
      </div>
    </FormProvider>
  );
}
