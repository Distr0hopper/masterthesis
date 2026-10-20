import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Archive,
  ArchiveRestore,
  ChevronLeft,
  Download,
  ExternalLink,
  Globe,
  GlobeLock,
  FilePlus2,
  Pencil,
  PenLine,
  Trash2,
  Workflow as WorkflowIcon,
} from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { Button } from '@/components/ui/button.tsx';
import {
  ComponentSource,
  ComponentStatus,
  useDownloadComponent,
  usePublishComponent,
  useComponentVersions,
  newestVersion,
  usePublishImpact,
  useUndeprecateComponent,
  type ComponentDetailDisplayModel,
} from '@/api/components';
import { toolsService } from '@/api/tools';
import { StepMatchStatus, type ComponentSummaryDto } from '@/api/workflows';
import {
  canAddVersion,
  canFavorite,
  canDelete as hasDeleteLink,
  canDeprecate as hasDeprecateLink,
  canUndeprecate as hasUndeprecateLink,
  canPublish as hasPublishLink,
  canRepackage,
  canUnpublish as hasUnpublishLink,
  canUpdateDescription as hasUpdateDescriptionLink,
  canUpdateDomain as hasUpdateDomainLink,
  canUpdateFormatLabels as hasUpdateFormatLabelsLink,
  getLink,
} from '@/api/permissions';
import { getErrorMessage } from '@/lib/errors';
import { ROUTES, componentDetailRoute } from '@/lib/routes';
import { editableBuilderDraftId } from '@/lib/builderDraft';
import { downloadBlob } from '@/lib/download';
import { ComponentFavoriteButton } from '@/components/ComponentFavoriteButton';
import { DeleteComponentDialog } from '@/components/component-mine/organisms/DeleteComponentDialog';
import { ConfirmPublishDialog } from './ConfirmPublishDialog';
import { DomainBadges } from '@/components/common/DomainBadges';
import { StatusBadge } from '@/components/common/StatusBadge';
import { EditComponentDialog } from './EditComponentDialog';
import { DeprecateComponentDialog } from './DeprecateComponentDialog';
import { UnpublishComponentDialog } from './UnpublishComponentDialog';
import { VERSIONS_ANCHOR } from './ComponentVersions';

interface ComponentHeaderProps {
  model: ComponentDetailDisplayModel;
  backTo: string;
  backLabel: string;
  onDeleted: () => void;
}

const DRAFT_NOTICE: Record<ComponentDetailDisplayModel['kind'], string> = {
  tool: 'This tool is a draft and is only visible to you. Publish it to make it public and available in the Workflow Builder.',
  workflow:
    'This workflow is a draft and is only visible to you. Confirm every step below, then click Publish to make it public.',
};

const BUILDER_DRAFT_NOTICE =
  'This workflow is a draft and is only visible to you. Its steps are edited in the Workflow Builder - click Publish to make it public.';

/** The deprecated children a workflow's publish would give a new dependent - its direct steps' components. */
function deprecatedChildren(model: ComponentDetailDisplayModel): ComponentSummaryDto[] {
  if (model.kind !== 'workflow') return [];
  return model.steps
    .map((step) => step.component)
    .filter(
      (component): component is ComponentSummaryDto =>
        component !== null && component.status === ComponentStatus.DEPRECATED,
    );
}

/** The draft children a workflow's publish would have to take along - its direct steps' components. */
function draftChildren(model: ComponentDetailDisplayModel): ComponentSummaryDto[] {
  if (model.kind !== 'workflow') return [];
  return model.steps
    .map((step) => step.component)
    .filter(
      (component): component is ComponentSummaryDto =>
        component !== null && component.status === ComponentStatus.DRAFT,
    );
}

function builderSaveHint(head: { version: number; status: ComponentStatus; isTakenBack: boolean } | undefined): string {
  if (!head) return 'Open the canvas this workflow was saved from';
  // a version that was ever public stays as it was - even taken back to a draft
  if (head.status === ComponentStatus.DRAFT && !head.isTakenBack) {
    return `Saving in the builder updates the draft v${head.version}`;
  }
  return `Saving in the builder creates v${head.version + 1} as a draft - v${head.version} stays unchanged`;
}

function newVersionHint(model: ComponentDetailDisplayModel): string {
  if (model.kind === 'workflow') return 'Upload the changed workflow as the next version';
  if (model.source === ComponentSource.AUTOMATED_PACKAGING) return 'Package the repository again as the next version';
  return 'Upload a changed CWL file as the next version';
}

function publishBlockedHint(allStepsSettled: boolean, editedInBuilder: boolean): string | undefined {
  if (allStepsSettled) return undefined;
  if (editedInBuilder) return 'A step lost its component - replace it in the Workflow Builder first';
  return 'Confirm every step before publishing';
}

export function ComponentHeader({ model, backTo, backLabel, onDeleted }: ComponentHeaderProps) {
  const { mutate: publishComponent, isPending: isPublishing } = usePublishComponent();
  const { mutate: downloadComponent, isPending: isDownloading } = useDownloadComponent();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [publishDialogOpen, setPublishDialogOpen] = useState(false);
  const [unpublishDialogOpen, setUnpublishDialogOpen] = useState(false);
  const [deprecateDialogOpen, setDeprecateDialogOpen] = useState(false);
  const { mutate: undeprecateComponent, isPending: isUndeprecating } = useUndeprecateComponent();

  const navigate = useNavigate();
  const { data: versions } = useComponentVersions(model.id);
  const versionCount = versions?.length ?? 0;
  const builderDraftId = editableBuilderDraftId(model);
  const head = newestVersion(versions);
  const isWorkflow = model.kind === 'workflow';
  const canCreateVersion = canAddVersion(model._links) || canRepackage(model._links);
  const newVersionRoute = isWorkflow ? ROUTES.workflowNewVersion(model.id) : ROUTES.toolNewVersion(model.id);
  const canDelete = hasDeleteLink(model._links);
  const canEdit =
    hasUpdateDescriptionLink(model._links) ||
    hasUpdateDomainLink(model._links) ||
    hasUpdateFormatLabelsLink(model._links);
  // a workflow publishes only once every step is settled - a tool has none to settle
  const allStepsSettled =
    !isWorkflow ||
    model.steps.every(
      (step) => step.matchStatus === StepMatchStatus.CONFIRMED || step.matchStatus === StepMatchStatus.INLINE,
    );
  const canPublish = hasPublishLink(model._links) && model.status === ComponentStatus.DRAFT;
  // what the publish would deprecate - read once its dialog opens, like the delete dialog's impact
  const { data: publishImpact, isLoading: isLoadingPublishImpact } = usePublishImpact(
    getLink(model._links, 'publishImpact'),
    canPublish && publishDialogOpen,
  );
  const supersedes = publishImpact?.supersedes ?? [];
  const canUnpublish = hasUnpublishLink(model._links) && model.status === ComponentStatus.PUBLISHED;
  const canDeprecate = hasDeprecateLink(model._links) && model.status === ComponentStatus.PUBLISHED;
  const canUndeprecate = hasUndeprecateLink(model._links) && model.status === ComponentStatus.DEPRECATED;
  const deprecated = deprecatedChildren(model);

  const drafts = draftChildren(model);
  const blockedByOthers = drafts.filter((component) => !component.canPublish);

  const doPublish = (publishComponents = false) => {
    publishComponent(
      { link: getLink(model._links, 'publish')!, publishComponents },
      {
        onSuccess: () => {
          setPublishDialogOpen(false);
          const published =
            publishComponents && drafts.length > 0
              ? `${model.kindDisplay} published, along with the draft components it runs`
              : `${model.kindDisplay} published`;
          const deprecatedLabels = supersedes.map((s) => (s.name === model.name ? `v${s.version}` : `${s.name} v${s.version}`));
          toast.success(
            deprecatedLabels.length > 0 ? `${published} - ${deprecatedLabels.join(', ')} deprecated` : published,
          );
        },
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  };

  const handleUndeprecate = () => {
    undeprecateComponent(getLink(model._links, 'undeprecate')!, {
      onSuccess: () => toast.success(`${model.kindDisplay} is listed and usable in new workflows again`),
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  };

  const handleDownload = () => {
    downloadComponent(model.id, {
      onSuccess: ({ blob, filename }) => downloadBlob(filename, blob),
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  };

  return (
    <>
      <Link to={backTo} className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900">
        <ChevronLeft className="h-4 w-4" /> {backLabel}
      </Link>
      {model.status === ComponentStatus.DRAFT && (
        <div className="mt-4 rounded-md border border-jmu-blue-200 bg-jmu-blue-50 px-4 py-3 text-sm text-jmu-blue-900">
          {model.isTakenBack && !model.supersededBy ? (
            // taken back after it was public - hidden again, but its content is frozen for good
            <>
              This version was published and has been taken back - only you see it now. What others saw as v
              {model.version} doesn&apos;t change anymore: publish it again, or put changes into{' '}
              {builderDraftId ? (
                <Link to={ROUTES.builderWorkflow(builderDraftId)} className="font-medium underline">
                  a new version from the Workflow Builder
                </Link>
              ) : canCreateVersion ? (
                <Link to={newVersionRoute} className="font-medium underline">
                  a new version
                </Link>
              ) : (
                'a new version'
              )}
              .
            </>
          ) : model.supersededBy ? (
            // no Publish button here - a newer version is published, so this one is superseded
            <>
              This version is a draft and only visible to you.{' '}
              <Link to={componentDetailRoute(model.kind, model.supersededBy.id)} className="font-medium underline">
                v{model.supersededBy.version}
              </Link>{' '}
              is already published, so this older version can't be published anymore.
            </>
          ) : (
            builderDraftId ? BUILDER_DRAFT_NOTICE : DRAFT_NOTICE[model.kind]
          )}
        </div>
      )}

      {model.status === ComponentStatus.DEPRECATED && (
        <div role="status" className="mt-4 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <p className="font-medium">
            This version is deprecated{model.deprecationNote ? `: ${model.deprecationNote}` : '.'}
          </p>
          <p className="mt-1">
            Workflows that already run it keep working, but it is no longer listed and can't be used in new workflows.
            {model.supersededBy && (
              <>
                {' '}
                The current version is{' '}
                <Link to={componentDetailRoute(model.kind, model.supersededBy.id)} className="font-medium underline">
                  v{model.supersededBy.version}
                </Link>
                .
              </>
            )}
          </p>
        </div>
      )}

      <Card className="mt-4">
        <CardContent className="flex flex-col gap-3 pt-6">
          <div className="flex items-center justify-between">
            <div className="flex flex-wrap items-center gap-2">
              <DomainBadges domains={model.domains} />

              {isWorkflow && (
                <Badge variant="secondary" className="w-fit gap-1">
                  {model.source === ComponentSource.WORKFLOW_BUILDER && <WorkflowIcon className="h-3 w-3" aria-hidden />}
                  {model.sourceDisplay}
                </Badge>
              )}

              <Badge variant="outline" className="w-fit" title="Version of this lineage">
                v{model.version}
              </Badge>
              <StatusBadge status={model.status} label={model.statusDisplay} hint={model.statusHint} />
              {versionCount > 1 && (
                <a href={`#${VERSIONS_ANCHOR}`} className="text-xs text-slate-500 hover:text-jmu-blue-800 hover:underline">
                  {versionCount} versions
                </a>
              )}

              {canFavorite(model._links) && <ComponentFavoriteButton links={model._links!} isFavorite={model.isFavorite} />}
            </div>

            <div className="flex items-center gap-2">
              {model.kind === 'tool' ? (
                // the run bundle: the .cwl, an inputs.yaml template and its imported files
                <Button asChild variant="outline" size="sm">
                  <a href={toolsService.getBundleUrl(model.id)}>
                    <Download className="mr-1 h-4 w-4" /> Download
                  </a>
                </Button>
              ) : (
                // the whole tree: the pipeline, every step document below it - nested
                // workflows included - and everything they import
                <Button variant="outline" size="sm" onClick={handleDownload} disabled={isDownloading}>
                  <Download className="mr-1 h-4 w-4" /> Download
                </Button>
              )}

              {canCreateVersion && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate(newVersionRoute)}
                  title={newVersionHint(model)}
                >
                  <FilePlus2 className="mr-1 h-4 w-4" /> New version
                </Button>
              )}

              {builderDraftId && (
                <Button asChild variant="outline" size="sm" title={builderSaveHint(head)}>
                  <Link to={ROUTES.builderWorkflow(builderDraftId)}>
                    <PenLine className="mr-1 h-4 w-4" /> Edit in Workflow Builder
                  </Link>
                </Button>
              )}

              {canEdit && (
                <Button variant="outline" size="sm" onClick={() => setEditDialogOpen(true)}>
                  <Pencil className="mr-1 h-4 w-4" /> Edit
                </Button>
              )}

              {canPublish && (
                <Button
                  size="sm"
                  className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
                  // always confirmed, like unpublish, deprecate and delete - it makes the version visible to everyone
                  onClick={() => setPublishDialogOpen(true)}
                  disabled={isPublishing || !allStepsSettled}
                  title={publishBlockedHint(allStepsSettled, !!builderDraftId)}
                >
                  <Globe className="mr-1 h-4 w-4" /> Publish
                </Button>
              )}

              {canUnpublish && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setUnpublishDialogOpen(true)}
                  title={`Hide this ${model.kindDisplay.toLowerCase()} from the public list and the Workflow Builder again`}
                >
                  <GlobeLock className="mr-1 h-4 w-4" /> Unpublish
                </Button>
              )}

              {canDeprecate && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setDeprecateDialogOpen(true)}
                  title="Stop offering this version for new workflows - existing ones keep working"
                >
                  <Archive className="mr-1 h-4 w-4" /> Deprecate
                </Button>
              )}

              {canUndeprecate && (
                <>
                  <Button variant="outline" size="sm" onClick={() => setDeprecateDialogOpen(true)}>
                    <Pencil className="mr-1 h-4 w-4" /> Edit note
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleUndeprecate} disabled={isUndeprecating}>
                    <ArchiveRestore className="mr-1 h-4 w-4" /> Undeprecate
                  </Button>
                </>
              )}

              {canDelete && (
                <Button variant="destructive" size="sm" onClick={() => setDeleteDialogOpen(true)}>
                  <Trash2 className="mr-1 h-4 w-4" /> Delete
                </Button>
              )}
            </div>
          </div>

          <h1 className="font-mono text-2xl font-bold text-slate-900">{model.name}</h1>

          {model.description && <p className="text-slate-600">{model.description}</p>}

          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t pt-3 text-sm text-slate-500">
            <span>{model.authorDisplay}</span>
            <span>Created {model.createdAtDisplay}</span>
            <span>Updated {model.updatedAtDisplay}</span>
            {model.repoUrl && (
              <a
                href={model.repoUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-jmu-blue-800 hover:underline"
              >
                <ExternalLink className="h-4 w-4" /> GitHub
              </a>
            )}
            {model.repoCommitShaShort && (
              <Badge variant="secondary" className="font-mono">
                {model.repoCommitShaShort}
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>

      <DeleteComponentDialog
        component={model}
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        onDeleted={onDeleted}
        onDeprecateInstead={() => setDeprecateDialogOpen(true)}
      />
      <EditComponentDialog component={model} open={editDialogOpen} onOpenChange={setEditDialogOpen} />
      {canUnpublish && (
        <UnpublishComponentDialog
          model={model}
          open={unpublishDialogOpen}
          onOpenChange={setUnpublishDialogOpen}
          onDeprecateInstead={() => setDeprecateDialogOpen(true)}
        />
      )}
      <DeprecateComponentDialog component={model} open={deprecateDialogOpen} onOpenChange={setDeprecateDialogOpen} />
      {canPublish && (
        <ConfirmPublishDialog
          open={publishDialogOpen}
          onOpenChange={setPublishDialogOpen}
          component={model}
          supersedes={supersedes}
          isLoadingImpact={isLoadingPublishImpact}
          draftComponents={drafts}
          blockedByOthers={blockedByOthers}
          deprecatedComponents={deprecated}
          onConfirm={doPublish}
          isPending={isPublishing}
        />
      )}
    </>
  );
}
