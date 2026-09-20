import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronLeft, Download, Globe, GlobeLock, Pencil, Trash2, Workflow as WorkflowIcon } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { Button } from '@/components/ui/button.tsx';
import { getDomainBadgeStyle, useDomains } from '@/api/components';
import {
  StepMatchStatus,
  useDownloadWorkflow,
  usePublishWorkflow,
  useUnpublishWorkflow,
  WorkflowSource,
  WorkflowStatus,
  type WorkflowDetailDisplayModel,
} from '@/api/workflows';
import {
  canDelete as hasDeleteLink,
  canPublish as hasPublishLink,
  canUnpublish as hasUnpublishLink,
  canUpdateDescription as hasUpdateDescriptionLink,
  getLink,
} from '@/api/permissions';
import { getErrorMessage } from '@/lib/errors';
import { downloadBlob } from '@/lib/download';
import { DeleteWorkflowDialog } from '@/components/workflow-mine/organisms/DeleteWorkflowDialog';
import { EditWorkflowDescriptionDialog } from './EditWorkflowDescriptionDialog';

interface WorkflowHeaderProps {
  model: WorkflowDetailDisplayModel;
  backTo: string;
  backLabel: string;
  onDeleted: () => void;
}

export function WorkflowHeader({ model, backTo, backLabel, onDeleted }: WorkflowHeaderProps) {
  const { data: domains } = useDomains();
  const { mutate: publishWorkflow, isPending: isPublishing } = usePublishWorkflow();
  const { mutate: unpublishWorkflow, isPending: isUnpublishing } = useUnpublishWorkflow();
  const { mutate: downloadWorkflow, isPending: isDownloading } = useDownloadWorkflow();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editDescriptionDialogOpen, setEditDescriptionDialogOpen] = useState(false);

  const canDelete = hasDeleteLink(model._links);
  const canEdit = hasUpdateDescriptionLink(model._links);
  const allStepsConfirmed = model.steps.every((step) => step.matchStatus === StepMatchStatus.CONFIRMED);
  const canPublish = hasPublishLink(model._links) && model.status === WorkflowStatus.PENDING_VALIDATION;
  const canUnpublish = hasUnpublishLink(model._links) && model.status === WorkflowStatus.VALIDATED;

  const handlePublish = () => {
    publishWorkflow(getLink(model._links, 'publish')!, {
      onSuccess: () => toast.success('Workflow published'),
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  };

  const handleUnpublish = () => {
    unpublishWorkflow(getLink(model._links, 'unpublish')!, {
      onSuccess: () => toast.success('Workflow unpublished'),
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  };

  const handleDownload = () => {
    downloadWorkflow(model.id, {
      onSuccess: ({ blob, filename }) => downloadBlob(filename, blob),
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  };

  return (
    <>
      <Link to={backTo} className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900">
        <ChevronLeft className="h-4 w-4" /> {backLabel}
      </Link>

      {model.status === WorkflowStatus.PENDING_VALIDATION && (
        <div className="mt-4 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          This workflow is pending validation and is only visible to you. Confirm every step below, then click
          Publish to make it public.
        </div>
      )}

      <Card className="mt-4">
        <CardContent className="flex flex-col gap-3 pt-6">
          <div className="flex items-center justify-between">
            <div className="flex flex-wrap items-center gap-2">
              {model.domains.map((domainId, index) => (
                <Badge
                  key={domainId}
                  variant="outline"
                  className="w-fit"
                  style={domains ? getDomainBadgeStyle(domainId, domains) : undefined}
                >
                  {model.domainsDisplay[index]}
                </Badge>
              ))}

              <Badge variant="secondary" className="w-fit gap-1">
                {model.source === WorkflowSource.WORKFLOW_BUILDER && (
                  <WorkflowIcon className="h-3 w-3" aria-hidden />
                )}
                {model.sourceDisplay}
              </Badge>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={handleDownload} disabled={isDownloading}>
                <Download className="mr-1 h-4 w-4" /> Download
              </Button>

              {canEdit && (
                <Button variant="outline" size="sm" onClick={() => setEditDescriptionDialogOpen(true)}>
                  <Pencil className="mr-1 h-4 w-4" /> Edit
                </Button>
              )}

              {canPublish && (
                <Button
                  size="sm"
                  className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
                  onClick={handlePublish}
                  disabled={isPublishing || !allStepsConfirmed}
                  title={allStepsConfirmed ? undefined : 'Confirm every step before publishing'}
                >
                  <Globe className="mr-1 h-4 w-4" /> Publish
                </Button>
              )}

              {canUnpublish && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleUnpublish}
                  disabled={isUnpublishing}
                  title="Hide this workflow from the public list again"
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
            <span>{model.createdByDisplay}</span>
            <span>Created {model.createdAtDisplay}</span>
            <span>Updated {model.updatedAtDisplay}</span>
          </div>
        </CardContent>
      </Card>

      <DeleteWorkflowDialog workflow={model} open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen} onDeleted={onDeleted} />
      <EditWorkflowDescriptionDialog
        workflow={model}
        open={editDescriptionDialogOpen}
        onOpenChange={setEditDescriptionDialogOpen}
      />
    </>
  );
}
