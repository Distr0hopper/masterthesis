import { Link, useParams } from 'react-router-dom';
import { ChevronLeft, PenLine } from 'lucide-react';
import { Button } from '@/components/ui/button.tsx';
import { useLineageHead } from '@/api/components';
import { canAddVersion } from '@/api/permissions';
import { WorkflowUploadWizard } from '@/components/workflow-upload/organisms/WorkflowUploadWizard';
import { editableBuilderDraftId } from '@/lib/builderDraft';
import { ROUTES } from '@/lib/routes';

/**
 * The next version of an uploaded workflow, from a new upload - every step starts from what
 * it ran in the newest version, and a changed one can become its tool's next version. A
 * builder workflow gets its versions from saving the canvas instead, so it is sent there.
 */
export default function WorkflowNewVersionPage() {
  const { id = '' } = useParams<{ id: string }>();
  const { data: head, isLoading, error } = useLineageHead(id);

  const back = (
    <Link
      to={ROUTES.workflowDetail(id)}
      className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900"
    >
      <ChevronLeft className="h-4 w-4" /> Back to the workflow
    </Link>
  );

  if (isLoading) {
    return <p className="text-slate-500">Loading...</p>;
  }

  if (error || !head || head.kind !== 'workflow') {
    return (
      <div>
        {back}
        <p className="mt-4 text-slate-500">Workflow not found.</p>
      </div>
    );
  }

  const fromUpload = canAddVersion(head._links);
  const builderDraftId = editableBuilderDraftId(head);

  return (
    <div>
      {back}
      <h1 className="mt-4 text-2xl font-semibold text-slate-900">New version of {head.name}</h1>
      {fromUpload && (
        <p className="mt-1 text-slate-500">
          Upload the changed workflow - this creates version {head.version + 1}. Each step starts from what it ran in
          v{head.version}; a step whose tool changed can become that tool&apos;s next version. Everything new starts as
          a draft, only visible to you until you publish it.
        </p>
      )}

      <div className="mt-6">
        {fromUpload ? (
          <WorkflowUploadWizard parent={head} />
        ) : builderDraftId ? (
          <div className="flex flex-col items-start gap-3 rounded-md bg-slate-50 px-4 py-3 text-sm text-slate-700">
            <p>
              This workflow is edited in the Workflow Builder - saving its canvas creates the next version once v
              {head.version} has been published - even if it was taken back since.
            </p>
            <Button asChild variant="outline" size="sm">
              <Link to={ROUTES.builderWorkflow(builderDraftId)}>
                <PenLine className="mr-1 h-4 w-4" /> Edit in Workflow Builder
              </Link>
            </Button>
          </div>
        ) : (
          <p className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
            Only the owner of this workflow can add new versions to it.
          </p>
        )}
      </div>
    </div>
  );
}
