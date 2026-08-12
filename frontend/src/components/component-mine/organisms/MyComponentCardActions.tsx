import { useState } from 'react';
import { Pencil, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button.tsx';
import type { ComponentDisplayModel } from '@/api/components';
import { EditComponentDialog } from './EditComponentDialog';
import { DeleteComponentDialog } from './DeleteComponentDialog';

interface MyComponentCardActionsProps {
  component: ComponentDisplayModel;
}

export function MyComponentCardActions({ component }: MyComponentCardActionsProps) {
  const [openDialog, setOpenDialog] = useState<'edit' | 'delete' | null>(null);

  return (
    <>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" className="flex-1" onClick={() => setOpenDialog('edit')}>
          <Pencil className="mr-1 h-4 w-4" /> Edit
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="flex-1 text-destructive hover:text-destructive"
          onClick={() => setOpenDialog('delete')}
        >
          <Trash2 className="mr-1 h-4 w-4" /> Delete
        </Button>
      </div>

      <EditComponentDialog component={component} open={openDialog === 'edit'} onOpenChange={(open) => setOpenDialog(open ? 'edit' : null)} />
      <DeleteComponentDialog
        component={component}
        open={openDialog === 'delete'}
        onOpenChange={(open) => setOpenDialog(open ? 'delete' : null)}
      />
    </>
  );
}
