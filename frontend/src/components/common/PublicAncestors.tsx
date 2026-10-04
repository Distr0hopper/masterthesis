import { AlertTriangle, Ban } from 'lucide-react';
import { ComponentLink } from '@/components/common/ComponentLink';
import { getCreatorDisplay } from '@/api/transformer';
import type { ComponentAncestorDto, ComponentImpactDto } from '@/api/components';

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
        </li>
      ))}
    </ul>
  );
}

/**
 * The public workflows above a version, at any depth - what unpublishing or deleting it
 * would break. Other users' block the action outright; the user's own go down with it.
 * `verb` is the action in progress, e.g. "Unpublishing" or "Deleting".
 */
export function PublicAncestors({ impact, verb }: { impact: ComponentImpactDto; verb: string }) {
  const own = impact.ownPublicAncestors;
  const foreign = impact.foreignPublicAncestors;

  if (foreign.length > 0) {
    return (
      <div role="alert" className="space-y-2 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900">
        <div className="flex items-start gap-2 font-medium">
          <Ban className="mt-0.5 h-4 w-4 shrink-0 text-red-600" aria-hidden />
          <span>
            Used by {plural(foreign.length, 'published workflow')} of another user. {verb} it would break their
            workflow, so it isn't possible.
          </span>
        </div>
        <AncestorList ancestors={foreign} withOwner />
        <p>If you need to retract this version, contact the workflow owners or publish a fixed version.</p>
      </div>
    );
  }

  if (own.length > 0) {
    return (
      <div role="alert" className="space-y-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
        <div className="flex items-start gap-2 font-medium">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" aria-hidden />
          <span>
            Used by {own.length} of your published {own.length === 1 ? 'workflow' : 'workflows'}.{' '}
            {own.length === 1 ? 'It' : 'They'} will also become {own.length === 1 ? 'a draft' : 'drafts'}.
          </span>
        </div>
        <AncestorList ancestors={own} withOwner={false} />
      </div>
    );
  }

  return null;
}
