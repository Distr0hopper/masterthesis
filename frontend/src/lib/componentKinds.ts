import type { ComponentKind } from '@/api/components/types';

/** The wording that differs between the two kinds of component on otherwise shared pages. */
export interface KindCopy {
  /** "Tool" / "Workflow" */
  singular: string;
  /** "Tools" / "Workflows" */
  plural: string;
  /** "tools" / "workflows" - mid-sentence */
  pluralLower: string;
  browseSubtitle: string;
  mineSubtitle: string;
  uploadLabel: string;
}

export const KIND_COPY: Record<ComponentKind, KindCopy> = {
  tool: {
    singular: 'Tool',
    plural: 'Tools',
    pluralLower: 'tools',
    browseSubtitle: 'Reusable CWL building blocks for your workflows.',
    mineSubtitle: "Tools you've uploaded or packaged, including drafts that are still only visible to you.",
    uploadLabel: 'Upload Tool',
  },
  workflow: {
    singular: 'Workflow',
    plural: 'Workflows',
    pluralLower: 'workflows',
    browseSubtitle: 'Pipelines composed of tools - and of other workflows.',
    mineSubtitle:
      "Workflows you've uploaded or built in the Workflow Builder, including drafts that are still only visible to you.",
    uploadLabel: 'Upload Workflow',
  },
};
