import { ComponentSource, type ComponentDisplayModel } from '@/api/components';
import { canDelete } from '@/api/permissions';

/**
 * The builder draft the viewer can open to edit this component, or null. All three are
 * required:
 *  - a workflow that came from the builder,
 *  - whose draft still exists (the FK is ON DELETE SET NULL, so a deleted draft leaves the
 *    workflow intact but no longer editable),
 *  - and that the viewer owns. Drafts are owner-scoped, so the link would 404 for anyone
 *    else - `canDelete` is this codebase's ownership signal, only the owner gets that link.
 */
export function editableBuilderDraftId(component: ComponentDisplayModel): string | null {
  if (component.kind !== 'workflow' || component.source !== ComponentSource.WORKFLOW_BUILDER) return null;
  return canDelete(component._links) ? component.draftId : null;
}
