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
import type { ComponentSummaryDto } from '@/api/workflows';

interface ConfirmPublishDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  draftComponents: ComponentSummaryDto[];
  blockedByOthers: ComponentSummaryDto[];
  /** deprecated components its steps run - publishing would give them a new dependent */
  deprecatedComponents: ComponentSummaryDto[];
  onConfirm: (publishComponents: boolean) => void;
  isPending: boolean;
}

/**
 * The last gate before a workflow goes public, and the only one a builder-synced workflow
 * passes through - it never sees the upload form's checks.
 *
 * Draft components are a hard blocker: a public workflow pointing at owner-only drafts is
 * broken for everyone else - tools and nested workflows alike. Only the direct children
 * are listed; the backend checks the whole tree and names any deeper drafts itself.
 */
export function ConfirmPublishDialog({
  open,
  onOpenChange,
  draftComponents,
  blockedByOthers,
  deprecatedComponents,
  onConfirm,
  isPending,
}: ConfirmPublishDialogProps) {
  const hasDrafts = draftComponents.length > 0;
  const runsDeprecated = deprecatedComponents.length > 0;
  // a draft owned by someone else, or a deprecated component, cannot be resolved here at
  // all - only replacing the step does
  const isBlocked = blockedByOthers.length > 0 || runsDeprecated;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isBlocked ? 'This workflow cannot be published yet' : 'Publish this workflow?'}</DialogTitle>
          <DialogDescription>
            {runsDeprecated
              ? 'It runs deprecated components. They keep working where they already run, but a newly published workflow must not depend on them - replace these steps with newer versions first.'
              : isBlocked
              ? 'It uses draft components owned by someone else. Only their creator can publish them, so ask them to before publishing this workflow.'
              : hasDrafts
                ? 'A published workflow must not point at draft components - nobody else can see those. Publishing these along with it makes the whole workflow usable.'
                : 'This workflow will become visible to everyone.'}
          </DialogDescription>
        </DialogHeader>

        {runsDeprecated && (
          <ul className="divide-y rounded-md border border-input">
            {deprecatedComponents.map((component) => (
              <li key={component.id} className="flex flex-col gap-0.5 px-3 py-2">
                <ComponentLink
                  componentId={component.id}
                  kind={component.kind}
                  name={component.name}
                  version={component.version}
                />
                <span className="text-xs text-slate-600">
                  deprecated{component.deprecationNote ? `: ${component.deprecationNote}` : ''}
                </span>
              </li>
            ))}
          </ul>
        )}

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
                    kind={component.kind}
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
