import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button.tsx';
import { canDelete } from '@/api/permissions';
import type { WorkflowDisplayModel } from '@/api/workflows';
import { DeleteWorkflowDialog } from './DeleteWorkflowDialog';

interface MyWorkflowCardActionsProps {
  workflow: WorkflowDisplayModel;
}

export function MyWorkflowCardActions({ workflow }: MyWorkflowCardActionsProps) {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  if (!canDelete(workflow._links)) return null;

  return (
    <>
      <Button variant="destructive" size="sm" className="w-full" onClick={() => setDeleteDialogOpen(true)}>
        <Trash2 className="mr-1 h-4 w-4" /> Delete
      </Button>

      <DeleteWorkflowDialog workflow={workflow} open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen} />
    </>
  );
}
