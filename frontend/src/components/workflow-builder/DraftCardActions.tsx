import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button.tsx';
import type { WorkflowDraftListItemDto } from '@/api/workflow-drafts';
import { DeleteDraftDialog } from './DeleteDraftDialog';

interface DraftCardActionsProps {
  draft: WorkflowDraftListItemDto;
}

export function DraftCardActions({ draft }: DraftCardActionsProps) {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  return (
    <>
      <Button
        variant="destructive"
        size="sm"
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
