import type { ReactNode } from 'react';
import { AlertTriangle, Ban } from 'lucide-react';
import { ComponentLink } from '@/components/common/ComponentLink';
import { getCreatorDisplay } from '@/api/transformer';
import {
  ComponentStatus,
  ownDeprecatedAncestors,
  ownPublishedAncestors,
  type ComponentAncestorDto,
  type ComponentImpactDto,
} from '@/api/components';

function plural(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? '' : 's'}`;
}

function AncestorList({ ancestors, withOwner }: { ancestors: ComponentAncestorDto[]; withOwner: boolean }) {
  return (
    <ul className="mt-1 list-disc space-y-0.5 pl-5">
      {ancestors.map((ancestor) => (
        <li key={ancestor.id}>
          <ComponentLink componentId={ancestor.id} kind="workflow" name={ancestor.name} version={ancestor.version} />
          {withOwner && <span className="text-slate-600"> by {getCreatorDisplay(ancestor.createdBy)}</span>}
          {ancestor.status === ComponentStatus.DEPRECATED && <span className="text-slate-600"> (deprecated)</span>}
        </li>
      ))}
    </ul>
  );
}

/**
 * The public workflows above a version, at any depth - what unpublishing or deleting it
 * would break. Three cases, told apart by owner and status: other users' block the action
 * outright, your own deprecated ones block it too (a deprecated version never goes straight
 * back to draft), and your own published ones become drafts along with it.
 * `verb` is the action in progress, e.g. "Unpublishing" or "Deleting".
 */
export function PublicAncestors({ impact, verb }: { impact: ComponentImpactDto; verb: string }) {
  const foreign = impact.foreignPublicAncestors;
  const ownDeprecated = ownDeprecatedAncestors(impact);
  const ownPublished = ownPublishedAncestors(impact);
  const blocked = foreign.length > 0 || ownDeprecated.length > 0;

  return (
    <>
      {foreign.length > 0 && (
        <Notice tone="blocked">
          Used by {plural(foreign.length, 'public workflow')} of another user. {verb} it would break their workflow,
          so it isn't possible.
          <AncestorList ancestors={foreign} withOwner />
        </Notice>
      )}

      {ownDeprecated.length > 0 && (
        <Notice tone="blocked">
          Used by {plural(ownDeprecated.length, 'deprecated workflow')} of yours. A deprecated workflow can't become a
          draft - undeprecate {ownDeprecated.length === 1 ? 'it' : 'them'} first, or deprecate this version instead.
          <AncestorList ancestors={ownDeprecated} withOwner={false} />
        </Notice>
      )}

      {blocked && (
        <p className="text-sm text-slate-600">
          To retract this version without breaking anything, deprecate it: workflows using it keep working, but it
          is no longer offered for new ones. Or contact the workflow owners, or publish a fixed version.
        </p>
      )}

      {!blocked && ownPublished.length > 0 && (
        <Notice tone="warning">
          Used by {ownPublished.length} of your published {ownPublished.length === 1 ? 'workflow' : 'workflows'}.{' '}
          {ownPublished.length === 1 ? 'It' : 'They'} will also become {ownPublished.length === 1 ? 'a draft' : 'drafts'}.
          <AncestorList ancestors={ownPublished} withOwner={false} />
        </Notice>
      )}
    </>
  );
}

function Notice({ tone, children }: { tone: 'blocked' | 'warning'; children: ReactNode }) {
  const blocked = tone === 'blocked';
  const Icon = blocked ? Ban : AlertTriangle;
  return (
    <div
      role="alert"
      className={
        blocked
          ? 'rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900'
          : 'rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900'
      }
    >
      <div className="flex items-start gap-2">
        <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${blocked ? 'text-red-600' : 'text-amber-600'}`} aria-hidden />
        <div className="space-y-1">{children}</div>
      </div>
    </div>
  );
}
