import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog.tsx';
import { Button } from '@/components/ui/button.tsx';
import { Textarea } from '@/components/ui/textarea.tsx';
import { ComponentStatus, useDeprecateComponent, type ComponentDisplayModelBase } from '@/api/components';
import { getLink } from '@/api/permissions';
import { getErrorMessage } from '@/lib/errors';

/** Mirrors MAX_DEPRECATION_NOTE_LENGTH in the backend. */
const MAX_NOTE_LENGTH = 500;

interface DeprecateComponentDialogProps {
  component: ComponentDisplayModelBase;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * Retracting a version without breaking anyone: unlike unpublishing, nothing already
 * running it stops working - it is just no longer listed or offered for new use. The
 * note tells everyone who still sees or runs it why, and what to use instead. Opening
 * this on an already deprecated version edits the note.
 */
export function DeprecateComponentDialog({ component, open, onOpenChange }: DeprecateComponentDialogProps) {
  const { mutate: deprecate, isPending } = useDeprecateComponent();
  const [note, setNote] = useState('');
  const isDeprecated = component.status === ComponentStatus.DEPRECATED;

  // a dialog instance outlives one deprecation - reopening starts from the stored note
  useEffect(() => {
    if (open) setNote(component.deprecationNote ?? '');
  }, [open, component.deprecationNote]);

  const handleConfirm = () => {
    deprecate(
      { link: getLink(component._links, 'deprecate')!, deprecationNote: note.trim() || null },
      {
        onSuccess: () => {
          onOpenChange(false);
          toast.success(
            isDeprecated
              ? 'Deprecation note updated'
              : `${component.name} v${component.version} deprecated - workflows using it keep working`,
          );
        },
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {isDeprecated ? `Edit the deprecation note of ${component.name}` : `Deprecate ${component.name} v${component.version}?`}
          </DialogTitle>
          <DialogDescription>
            It stays readable and keeps working in every workflow that already runs it, but it is no longer listed in
            the catalogue or offered in the Workflow Builder, and no new workflow can use it. You can undeprecate it
            at any time.
          </DialogDescription>
        </DialogHeader>

        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium text-slate-900">Reason (optional)</span>
          <Textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            maxLength={MAX_NOTE_LENGTH}
            rows={3}
            placeholder="e.g. Wrong CRS handling - use v3 instead"
          />
          <span className="text-xs text-slate-500">
            Shown to everyone who opens this version or runs it in a workflow. {note.length}/{MAX_NOTE_LENGTH}
          </span>
        </label>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            Cancel
          </Button>
          <Button type="button" onClick={handleConfirm} disabled={isPending}>
            {isPending ? 'Saving...' : isDeprecated ? 'Save note' : 'Deprecate'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
