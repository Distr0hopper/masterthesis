import { Archive, Info } from 'lucide-react';
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
import { KindBadge } from '@/components/common/KindBadge';
import type { ComponentDisplayModelBase, SupersededVersionDto } from '@/api/components';
import type { ComponentSummaryDto } from '@/api/workflows';

interface ConfirmPublishDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  component: Pick<ComponentDisplayModelBase, 'kind' | 'kindDisplay' | 'name' | 'version'>;
  /** older published versions the publish deprecates - see GET /components/{id}/publish-impact */
  supersedes: SupersededVersionDto[];
  /** the publish impact is still loading - nothing to confirm yet */
  isLoadingImpact: boolean;
  /** workflows only: the draft components its steps run */
  draftComponents?: ComponentSummaryDto[];
  blockedByOthers?: ComponentSummaryDto[];
  /** workflows only: deprecated components its steps run - publishing would give them a new dependent */
  deprecatedComponents?: ComponentSummaryDto[];
  onConfirm: (publishComponents: boolean) => void;
  isPending: boolean;
}

function plural(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? '' : 's'}`;
}

/** The primary button says exactly what it will do - including what it deprecates. */
function confirmLabel(
  component: ConfirmPublishDialogProps['component'],
  supersedes: SupersededVersionDto[],
  hasDrafts: boolean,
): string {
  const publish = hasDrafts ? 'Publish all' : 'Publish';
  if (supersedes.length === 0) return publish;
  const [only] = supersedes;
  if (supersedes.length === 1 && only.name === component.name) {
    return `Publish v${component.version} and deprecate v${only.version}`;
  }
  return `${publish} and deprecate ${plural(supersedes.length, 'version')}`;
}

/**
 * The last gate before a version goes public - for either kind, like the unpublish,
 * deprecate and delete dialogs.
 *
 * Older published versions of the lineage are deprecated by the publish: named here, with
 * what that means for the workflows running them, so nothing changes unannounced. For a
 * workflow, draft components are a hard blocker: a public workflow pointing at owner-only
 * drafts is broken for everyone else - tools and nested workflows alike. Only the direct
 * children are listed; the backend checks the whole tree and names any deeper drafts itself.
 */
export function ConfirmPublishDialog({
  open,
  onOpenChange,
  component,
  supersedes,
  isLoadingImpact,
  draftComponents = [],
  blockedByOthers = [],
  deprecatedComponents = [],
  onConfirm,
  isPending,
}: ConfirmPublishDialogProps) {
  const kind = component.kindDisplay.toLowerCase();
  const hasDrafts = draftComponents.length > 0;
  const runsDeprecated = deprecatedComponents.length > 0;
  // a draft owned by someone else, or a deprecated component, cannot be resolved here at
  // all - only replacing the step does
  const isBlocked = blockedByOthers.length > 0 || runsDeprecated;
  const deprecates = !isBlocked && supersedes.length > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {isBlocked ? `This ${kind} cannot be published yet` : `Publish ${component.name} v${component.version}?`}
          </DialogTitle>
          <DialogDescription>
            {runsDeprecated
              ? 'It runs deprecated components. They keep working where they already run, but a newly published workflow must not depend on them - replace these steps with newer versions first.'
              : isBlocked
                ? 'It uses draft components owned by someone else. Only their creator can publish them, so ask them to before publishing this workflow.'
                : hasDrafts
                  ? 'A published workflow must not point at draft components - nobody else can see those. Publishing these along with it makes the whole workflow usable.'
                  : deprecates
                    ? 'It becomes visible to everyone and replaces the older version in the catalogue and the Workflow Builder.'
                    : `This ${kind} will become visible to everyone.`}
          </DialogDescription>
        </DialogHeader>

        {isLoadingImpact && <p className="text-sm text-slate-500">Checking what publishing changes...</p>}

        {runsDeprecated && (
          <ul className="divide-y rounded-md border border-input">
            {deprecatedComponents.map((c) => (
              <li key={c.id} className="flex flex-col gap-0.5 px-3 py-2">
                <ComponentLink componentId={c.id} kind={c.kind} name={c.name} version={c.version} />
                <span className="text-xs text-slate-600">
                  deprecated{c.deprecationNote ? `: ${c.deprecationNote}` : ''}
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
              {draftComponents.map((c) => (
                <li key={c.id} className="flex items-center justify-between gap-2 px-3 py-2">
                  <ComponentLink componentId={c.id} kind={c.kind} name={c.name} version={c.version} />
                  {!c.canPublish && <span className="text-xs text-amber-700">owned by someone else</span>}
                </li>
              ))}
            </ul>
          </div>
        )}

        {deprecates && (
          <div className="flex flex-col gap-2">
            <p className="flex items-center gap-1.5 text-sm font-medium text-slate-900">
              <Archive className="h-4 w-4 text-slate-500" aria-hidden />
              {supersedes.length === 1 ? 'This version will be deprecated' : 'These versions will be deprecated'}
            </p>
            <ul className="divide-y rounded-md border border-input">
              {supersedes.map((s) => (
                <li key={s.id} className="flex flex-col gap-0.5 px-3 py-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <KindBadge kind={s.kind} />
                    <ComponentLink componentId={s.id} kind={s.kind} name={s.name} version={s.version} />
                  </div>
                  <span className="text-xs text-slate-600">
                    {s.workflowCount > 0
                      ? `Used in ${plural(s.workflowCount, 'workflow')} - they keep working.`
                      : 'Not used in any workflow.'}{' '}
                    Its note will read "Superseded by v{s.supersededByVersion}".
                  </span>
                </li>
              ))}
            </ul>

            <div className="flex items-start gap-2 rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-600">
              <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
              <span>
                A deprecated version stays readable and keeps running wherever it already runs, but it is no longer
                listed and can't be used in new workflows. To undo, unpublish v{component.version} - you can then
                undeprecate the older version again.
              </span>
            </div>
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
              disabled={isPending || isLoadingImpact}
              className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
            >
              {isPending ? 'Publishing...' : confirmLabel(component, supersedes, hasDrafts)}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
