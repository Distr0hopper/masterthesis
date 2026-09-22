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
import { ComponentLink } from '@/components/common/ComponentLink';
import type { ComponentSummaryDto, ExistingWorkflowDto } from '@/api/workflows';
import { ROUTES } from '@/lib/routes';

interface ConfirmPublishDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** another workflow already using this name, if any - advisory only */
  nameTaken: ExistingWorkflowDto | null;
  draftComponents: ComponentSummaryDto[];
  blockedByOthers: ComponentSummaryDto[];
  onConfirm: (publishComponents: boolean) => void;
  isPending: boolean;
}

/**
 * The last gate before a workflow goes public, and the only one a builder-synced workflow
 * passes through - it never sees the upload form's checks.
 *
 * Two very different things share it: draft components are a hard blocker (a public
 * workflow pointing at owner-only drafts is broken for everyone else), while a duplicate
 * name is merely worth knowing, since workflow names need not be unique.
 */
export function ConfirmPublishDialog({
  open,
  onOpenChange,
  nameTaken,
  draftComponents,
  blockedByOthers,
  onConfirm,
  isPending,
}: ConfirmPublishDialogProps) {
  const hasDrafts = draftComponents.length > 0;
  // a draft owned by someone else cannot be published here at all - no button will fix it
  const isBlocked = blockedByOthers.length > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isBlocked ? 'This workflow cannot be published yet' : 'Publish this workflow?'}</DialogTitle>
          <DialogDescription>
            {isBlocked
              ? 'It uses draft components owned by someone else. Only their creator can publish them, so ask them to before publishing this workflow.'
              : hasDrafts
                ? 'A published workflow must not point at draft components - nobody else can see those. Publishing these along with it makes the whole workflow usable.'
                : 'This workflow will become visible to everyone.'}
          </DialogDescription>
        </DialogHeader>

        {hasDrafts && (
          <div className="flex flex-col gap-2">
            <p className="text-sm font-medium text-slate-900">
              {isBlocked ? 'Draft components' : `${draftComponents.length} component(s) will also be published`}
            </p>
            <ul className="divide-y rounded-md border border-input">
              {draftComponents.map((component) => (
                <li key={component.id} className="flex items-center justify-between gap-2 px-3 py-2">
                  <ComponentLink
                    componentId={component.id}
                    name={component.name}
                    version={component.version}
                  />
                  {!component.canPublish && (
                    <span className="text-xs text-amber-700">owned by someone else</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {nameTaken && (
          <div className="flex flex-wrap items-center gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span className="flex flex-wrap items-center gap-1">
              A workflow named
              <a
                href={ROUTES.workflowDetail(nameTaken.id)}
                target="_blank"
                rel="noreferrer"
                title="Open it in a new tab"
                className="inline-flex items-center gap-1 font-mono font-semibold hover:underline"
              >
                {nameTaken.name}
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
              already exists - names do not have to be unique.
            </span>
          </div>
        )}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            {isBlocked ? 'Close' : 'Cancel'}
          </Button>
          {!isBlocked && (
            <Button
              type="button"
              onClick={() => onConfirm(hasDrafts)}
              disabled={isPending}
              className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
            >
              {isPending ? 'Publishing...' : hasDrafts ? 'Publish all' : 'Publish'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
