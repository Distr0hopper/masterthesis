import { AlertTriangle, ExternalLink } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog.tsx';
import { Button } from '@/components/ui/button.tsx';
import type { ExistingWorkflowDto } from '@/api/workflows';
import { ROUTES } from '@/lib/routes';

interface ConfirmPublishDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  existing: ExistingWorkflowDto;
  onConfirm: () => void;
  isPending: boolean;
}

/**
 * Publishing makes a workflow public, so a name already in use is worth surfacing first -
 * especially for builder-synced workflows, which never pass through the upload form where
 * the name is checked as you type.
 *
 * Advisory, like every other workflow name check: duplicates are legal, so this confirms
 * rather than refuses.
 */
export function ConfirmPublishDialog({
  open,
  onOpenChange,
  existing,
  onConfirm,
  isPending,
}: ConfirmPublishDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>That name is already in use</DialogTitle>
          <DialogDescription>
            Another workflow is already published under this name. Publishing anyway is allowed - workflow
            names do not have to be unique - but browsing users will see two entries with the same name.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-wrap items-center gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <a
            href={ROUTES.workflowDetail(existing.id)}
            target="_blank"
            rel="noreferrer"
            title="Open it in a new tab"
            className="inline-flex items-center gap-1 font-mono font-semibold hover:underline"
          >
            {existing.name}
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            Cancel
          </Button>
          <Button
            type="button"
            onClick={onConfirm}
            disabled={isPending}
            className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
          >
            {isPending ? 'Publishing...' : 'Publish anyway'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
