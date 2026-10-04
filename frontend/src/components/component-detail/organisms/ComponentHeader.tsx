import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ChevronLeft,
  Download,
  ExternalLink,
  Globe,
  GlobeLock,
  Pencil,
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
  type ComponentDetailDisplayModel,
} from '@/api/components';
import { toolsService } from '@/api/tools';
import { StepMatchStatus, type ComponentSummaryDto } from '@/api/workflows';
import {
  canFavorite,
  canDelete as hasDeleteLink,
  canPublish as hasPublishLink,
  canUnpublish as hasUnpublishLink,
  canUpdateDescription as hasUpdateDescriptionLink,
  canUpdateDomain as hasUpdateDomainLink,
  canUpdateFormatLabels as hasUpdateFormatLabelsLink,
  getLink,
} from '@/api/permissions';
import { getErrorMessage } from '@/lib/errors';
import { downloadBlob } from '@/lib/download';
import { ComponentFavoriteButton } from '@/components/ComponentFavoriteButton';
import { DeleteComponentDialog } from '@/components/component-mine/organisms/DeleteComponentDialog';
import { ConfirmPublishDialog } from '@/components/workflow-detail/organisms/ConfirmPublishDialog';
import { DomainBadges } from '@/components/common/DomainBadges';
import { EditComponentDialog } from './EditComponentDialog';
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

export function ComponentHeader({ model, backTo, backLabel, onDeleted }: ComponentHeaderProps) {
  const { mutate: publishComponent, isPending: isPublishing } = usePublishComponent();
  const { mutate: downloadComponent, isPending: isDownloading } = useDownloadComponent();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [publishDialogOpen, setPublishDialogOpen] = useState(false);
  const [unpublishDialogOpen, setUnpublishDialogOpen] = useState(false);

  const isWorkflow = model.kind === 'workflow';
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
  const canUnpublish = hasUnpublishLink(model._links) && model.status === ComponentStatus.PUBLISHED;

  // only the direct children are listed here; the backend checks the whole tree and names
  // any deeper drafts in its answer
  const drafts = draftChildren(model);
  const blockedByOthers = drafts.filter((component) => !component.canPublish);

  const doPublish = (publishComponents = false) => {
    publishComponent(
      { link: getLink(model._links, 'publish')!, publishComponents },
      {
        onSuccess: () => {
          setPublishDialogOpen(false);
          toast.success(
            publishComponents && drafts.length > 0
              ? `${model.kindDisplay} published, along with the draft components it runs`
              : `${model.kindDisplay} published`,
          );
        },
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  };

  const handlePublish = () => {
    if (drafts.length > 0) {
      setPublishDialogOpen(true);
      return;
    }
    doPublish();
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
        <div className="mt-4 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {DRAFT_NOTICE[model.kind]}
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

              {canEdit && (
                <Button variant="outline" size="sm" onClick={() => setEditDialogOpen(true)}>
                  <Pencil className="mr-1 h-4 w-4" /> Edit
                </Button>
              )}

              {canPublish && (
                <Button
                  size="sm"
                  className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
                  onClick={handlePublish}
                  disabled={isPublishing || !allStepsSettled}
                  title={allStepsSettled ? undefined : 'Confirm every step before publishing'}
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
      />
      <EditComponentDialog component={model} open={editDialogOpen} onOpenChange={setEditDialogOpen} />
      {canUnpublish && (
        <UnpublishComponentDialog model={model} open={unpublishDialogOpen} onOpenChange={setUnpublishDialogOpen} />
      )}
      {isWorkflow && (
        <ConfirmPublishDialog
          open={publishDialogOpen}
          onOpenChange={setPublishDialogOpen}
          draftComponents={drafts}
          blockedByOthers={blockedByOthers}
          onConfirm={doPublish}
          isPending={isPublishing}
        />
      )}
    </>
  );
}
