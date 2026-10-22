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
    // the card opens the canvas on click - nothing in here may trigger that, the dialog
    // included: its portal leaves the DOM, but React still bubbles its clicks up to the card.
    // `contents` keeps the buttons flex items of the card's footer
    <div className="contents" onClick={(e) => e.stopPropagation()}>
      {draft.linkedWorkflowId && (
        <Button asChild variant="outline" size="sm" title="Its page in My Components - publish it, set its details, see its versions">
          <Link
            to={componentDetailRoute(ComponentKind.WORKFLOW, draft.linkedWorkflowId)}
            state={{ from: ROUTES.builder }}
          >
            View in My Components
          </Link>
        </Button>
      )}
      <Button
        variant="destructive"
        size="sm"
        className="ml-auto"
        onClick={() => setDeleteDialogOpen(true)}
      >
        <Trash2 className="mr-1 h-4 w-4" /> Delete
      </Button>

      <DeleteDraftDialog draft={draft} open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen} />
    </div>
  );
}
