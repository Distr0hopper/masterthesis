import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button.tsx';
import { canDelete } from '@/api/permissions';
import type { ComponentDisplayModel } from '@/api/components';
import { DeprecateComponentDialog } from '@/components/component-detail/organisms/DeprecateComponentDialog';
import { DeleteComponentDialog } from './DeleteComponentDialog';

interface MyComponentCardActionsProps {
  component: ComponentDisplayModel;
}

export function MyComponentCardActions({ component }: MyComponentCardActionsProps) {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deprecateDialogOpen, setDeprecateDialogOpen] = useState(false);

  if (!canDelete(component._links)) return null;

  return (
    <>
      <Button variant="destructive" size="sm" className="w-full" onClick={() => setDeleteDialogOpen(true)}>
        <Trash2 className="mr-1 h-4 w-4" /> Delete
      </Button>

      <DeleteComponentDialog
        component={component}
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        onDeprecateInstead={() => setDeprecateDialogOpen(true)}
      />
      <DeprecateComponentDialog component={component} open={deprecateDialogOpen} onOpenChange={setDeprecateDialogOpen} />
    </>
  );
}
