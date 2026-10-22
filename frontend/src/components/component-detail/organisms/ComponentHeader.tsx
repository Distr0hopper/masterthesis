import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Archive,
  ArchiveRestore,
  ChevronDown,
  ChevronLeft,
  Download,
  ExternalLink,
  Globe,
  GlobeLock,
  MoreHorizontal,
  FilePlus2,
  Pencil,
  PenLine,
  Trash2,
} from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Button } from '@/components/ui/button.tsx';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
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
import { VersionSwitcher } from '@/components/common/VersionSwitcher';
import { KIND_ICONS } from '@/lib/componentKinds';
import { EditComponentDialog } from './EditComponentDialog';
import { DeprecateComponentDialog } from './DeprecateComponentDialog';
import { UnpublishComponentDialog } from './UnpublishComponentDialog';

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

function builderSaveHint(head: { version: number; status: ComponentStatus } | undefined): string {
  if (!head) return 'Open the canvas this workflow was saved from';
  if (head.status === ComponentStatus.DRAFT) {
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
  const KindIcon = KIND_ICONS[model.kind];
  const canCreateVersion = canAddVersion(model._links) || canRepackage(model._links);
  const newVersionRoute = isWorkflow ? ROUTES.workflowNewVersion(model.id) : ROUTES.toolNewVersion(model.id);
  const canDelete = hasDeleteLink(model._links);
  const canEdit =
    hasUpdateDescriptionLink(model._links) ||
    hasUpdateDomainLink(model._links) ||
    hasUpdateFormatLabelsLink(model._links);
  const allStepsSettled =
    !isWorkflow ||
    model.steps.every(
      (step) => step.matchStatus === StepMatchStatus.CONFIRMED || step.matchStatus === StepMatchStatus.INLINE,
    );
  const canPublish = hasPublishLink(model._links) && model.status === ComponentStatus.DRAFT;
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
          {model.supersededBy ? (
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
          {/* what it is, which version, and where that version stands - read top to bottom */}
          <div className="flex items-start justify-between gap-4">
            <div className="flex min-w-0 flex-col gap-1">
              <span className="inline-flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-slate-500">
                <KindIcon className="h-3.5 w-3.5" aria-hidden />
                {model.kindDisplay}
              </span>
              <h1 className="font-mono text-2xl font-bold text-slate-900">{model.name}</h1>
              {/* a lineage's versions can stand in different states - the state belongs to this one */}
              <div className="flex flex-wrap items-center gap-2">
                {versionCount > 1 ? (
                  <VersionSwitcher
                    componentId={model.id}
                    kind={model.kind}
                    version={model.version}
                    versionCount={versionCount}
                    backTo={backTo}
                      />
                ) : (
                  <span className="text-sm text-slate-400">v{model.version}</span>
                )}
                <StatusBadge status={model.status} />
                {model.unpublishableUntilDisplay && (
                  <span className="text-xs text-slate-500">
                    Can be unpublished until {model.unpublishableUntilDisplay} - after that only deprecated
                  </span>
                )}
              </div>
            </div>

            {canFavorite(model._links) && <ComponentFavoriteButton links={model._links!} isFavorite={model.isFavorite} />}
          </div>

          {model.description && <p className="text-slate-600">{model.description}</p>}

          {/* grouped by intent: the next step stands out, the rest waits in two menus */}
          <div className="flex flex-wrap items-center gap-2">
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
            {canUndeprecate && (
              <Button
                size="sm"
                className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
                onClick={handleUndeprecate}
                disabled={isUndeprecating}
              >
                <ArchiveRestore className="mr-1 h-4 w-4" /> Undeprecate
              </Button>
            )}

            {model.kind === 'tool' ? (
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

            {/* modal={false}: an item opens a dialog, and a modal menu would steal its focus back */}
            {(canEdit || canUndeprecate || canCreateVersion || builderDraftId) && (
              <DropdownMenu modal={false}>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Pencil className="mr-1 h-4 w-4" /> Edit <ChevronDown className="ml-1 h-3.5 w-3.5" aria-hidden />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-64">
                  {canEdit && (
                    <DropdownMenuItem className="cursor-pointer" onSelect={() => setEditDialogOpen(true)}>
                      <Pencil className="h-4 w-4 text-slate-500" /> Edit details
                    </DropdownMenuItem>
                  )}
                  {canUndeprecate && (
                    <DropdownMenuItem className="cursor-pointer" onSelect={() => setDeprecateDialogOpen(true)}>
                      <Pencil className="h-4 w-4 text-slate-500" /> Edit deprecation note
                    </DropdownMenuItem>
                  )}
                  {(canCreateVersion || builderDraftId) && (canEdit || canUndeprecate) && <DropdownMenuSeparator />}
                  {canCreateVersion && (
                    <DropdownMenuItem
                      className="cursor-pointer"
                      onSelect={() => navigate(newVersionRoute)}
                      title={newVersionHint(model)}
                    >
                      <FilePlus2 className="h-4 w-4 text-slate-500" /> New version
                    </DropdownMenuItem>
                  )}
                  {builderDraftId && (
                    <DropdownMenuItem className="cursor-pointer" asChild title={builderSaveHint(head)}>
                      <Link to={ROUTES.builderWorkflow(builderDraftId)}>
                        <PenLine className="h-4 w-4 text-slate-500" /> Edit in Workflow Builder
                      </Link>
                    </DropdownMenuItem>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            )}

            {(canUnpublish || canDeprecate || canDelete) && (
              <DropdownMenu modal={false}>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm" aria-label="More actions" title="More actions">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-64">
                  {canUnpublish && (
                    <DropdownMenuItem
                      className="cursor-pointer"
                      onSelect={() => setUnpublishDialogOpen(true)}
                      title={`Hide this ${model.kindDisplay.toLowerCase()} from the public list and the Workflow Builder again`}
                    >
                      <GlobeLock className="h-4 w-4 text-slate-500" /> Unpublish
                    </DropdownMenuItem>
                  )}
                  {canDeprecate && (
                    <DropdownMenuItem
                      className="cursor-pointer"
                      onSelect={() => setDeprecateDialogOpen(true)}
                      title="Stop offering this version for new workflows - existing ones keep working"
                    >
                      <Archive className="h-4 w-4 text-slate-500" /> Deprecate
                    </DropdownMenuItem>
                  )}
                  {canDelete && (
                    <>
                      {/* set apart at the bottom, in red - the one step that can't be undone */}
                      {(canUnpublish || canDeprecate) && <DropdownMenuSeparator />}
                      <DropdownMenuItem
                        onSelect={() => setDeleteDialogOpen(true)}
                        className="cursor-pointer text-red-600 focus:bg-red-50 focus:text-red-700"
                      >
                        <Trash2 className="h-4 w-4" /> Delete
                      </DropdownMenuItem>
                    </>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>

          {/* the facts, each named - a badge on its own doesn't say what it stands for */}
          <dl className="grid grid-cols-[max-content_1fr] items-center gap-x-6 gap-y-2 border-t pt-3 text-sm">
            <dt className="text-slate-500">Domains</dt>
            <dd className="flex flex-wrap gap-1.5">
              {model.domains.length > 0 ? <DomainBadges domains={model.domains} /> : <span className="text-slate-400">None</span>}
            </dd>

            <dt className="text-slate-500">Source</dt>
            <dd className="flex flex-wrap items-center gap-x-2 gap-y-1 text-slate-700">
              {model.sourceDisplay}
              {model.repoUrl && (
                <a
                  href={model.repoUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-jmu-blue-800 hover:underline"
                >
                  <ExternalLink className="h-3.5 w-3.5" aria-hidden /> GitHub
                </a>
              )}
              {model.repoCommitShaShort && (
                <span className="font-mono text-xs text-slate-500" title="Commit this version was packaged from">
                  {model.repoCommitShaShort}
                </span>
              )}
            </dd>

            <dt className="text-slate-500">Author</dt>
            <dd className="text-slate-700">{model.authorDisplay}</dd>

            <dt className="text-slate-500">Created</dt>
            <dd className="text-slate-700">
              {model.createdAtDisplay}
              <span className="text-slate-500"> · updated {model.updatedAtDisplay}</span>
            </dd>
          </dl>
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
          unpublishWindowSeconds={publishImpact?.unpublishWindowSeconds}
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
