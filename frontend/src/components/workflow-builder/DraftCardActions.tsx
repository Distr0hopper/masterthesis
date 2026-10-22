import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button.tsx';
import { ComponentKind } from '@/api/components';
import type { WorkflowDraftListItemDto } from '@/api/workflow-drafts';
import { ROUTES, componentDetailRoute } from '@/lib/routes';
import { DeleteDraftDialog } from './DeleteDraftDialog';

interface DraftCardActionsProps {
  draft: WorkflowDraftListItemDto;
}

export function DraftCardActions({ draft }: DraftCardActionsProps) {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  return (
    <>
      {draft.linkedWorkflowId && (
        <Button asChild variant="outline" size="sm" title="Its page in My Components - publish it, set its details, see its versions">
          <Link
            to={componentDetailRoute(ComponentKind.WORKFLOW, draft.linkedWorkflowId)}
            state={{ from: ROUTES.builder }}
            onClick={(e) => e.stopPropagation()}
          >
            View in My Components
          </Link>
        </Button>
      )}
      <Button
        variant="destructive"
        size="sm"
        className="ml-auto"
        onClick={(e) => {
          e.stopPropagation();
          setDeleteDialogOpen(true);
        }}
      >
        <Trash2 className="mr-1 h-4 w-4" /> Delete
      </Button>

      <DeleteDraftDialog draft={draft} open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen} />
    </>
  );
}
