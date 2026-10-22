import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog.tsx';
import { Button } from '@/components/ui/button.tsx';

interface UnsavedChangesDialogProps {
  open: boolean;
  onStay: () => void;
  onLeave: () => void;
  onSaveAndLeave: () => void;
  isSaving: boolean;
}

/** Asked before leaving the canvas with edits the last Save doesn't have. */
export function UnsavedChangesDialog({ open, onStay, onLeave, onSaveAndLeave, isSaving }: UnsavedChangesDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={(next) => !next && onStay()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Leave without saving?</AlertDialogTitle>
          <AlertDialogDescription>
            This workflow has changes that aren't saved yet. If you leave now, they are lost.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isSaving}>Stay</AlertDialogCancel>
          {/* not an AlertDialogAction: those close the dialog before the choice is carried out */}
          <Button variant="outline" onClick={onLeave} disabled={isSaving} className="text-red-600 hover:text-red-700">
            Discard changes
          </Button>
          <Button onClick={onSaveAndLeave} disabled={isSaving} className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90">
            {isSaving ? 'Saving...' : 'Save and leave'}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
