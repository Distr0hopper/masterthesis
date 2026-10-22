import { ComponentSource, type ComponentDisplayModel } from '@/api/components';
import { canEditInBuilder } from '@/api/permissions';

/**
 * The builder draft the viewer can open to edit this component, or null. The backend
 * offers the `builderDraft` link only to the owner of a workflow whose canvas still exists
 * (the FK is ON DELETE SET NULL), in every status - drafts are owner-scoped, so for anyone
 * else the canvas would 404.
 */
export function editableBuilderDraftId(component: ComponentDisplayModel): string | null {
  if (component.kind !== 'workflow' || component.source !== ComponentSource.WORKFLOW_BUILDER) return null;
  return canEditInBuilder(component._links) ? component.draftId : null;
}
