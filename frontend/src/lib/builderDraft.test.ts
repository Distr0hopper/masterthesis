import { describe, expect, it } from 'vitest';
import { ComponentSource, type ComponentDisplayModel } from '@/api/components';
import { editableBuilderDraftId } from './builderDraft';

function builderWorkflow(rels: string[]): ComponentDisplayModel {
  return {
    kind: 'workflow',
    source: ComponentSource.WORKFLOW_BUILDER,
    draftId: 'canvas-1',
    _links: Object.fromEntries(rels.map((rel) => [rel, { href: `/${rel}`, method: 'GET' }])),
  } as unknown as ComponentDisplayModel;
}

describe('the way back into the Workflow Builder', () => {
  it('stays open on a published version - it hangs on the builderDraft link, not on delete', () => {
    expect(editableBuilderDraftId(builderWorkflow(['self', 'builderDraft', 'deprecate']))).toBe('canvas-1');
  });

  it('is closed without the link - another user, or a deleted canvas', () => {
    expect(editableBuilderDraftId(builderWorkflow(['self', 'delete']))).toBeNull();
  });
});
