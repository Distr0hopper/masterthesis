import { Package, Workflow, type LucideIcon } from 'lucide-react';
import type { ComponentKind } from '@/api/components/types';

/** The wording that differs between the two kinds of component on otherwise shared pages. */
export interface KindCopy {
  /** "Tool" / "Workflow" */
  singular: string;
  /** "Tools" / "Workflows" */
  plural: string;
  /** "tools" / "workflows" - mid-sentence */
  pluralLower: string;
  mineSubtitle: string;
}

export const KIND_COPY: Record<ComponentKind, KindCopy> = {
  tool: {
    singular: 'Tool',
    plural: 'Tools',
    pluralLower: 'tools',
    mineSubtitle: "Tools you've uploaded or packaged, including drafts that are still only visible to you.",
  },
  workflow: {
    singular: 'Workflow',
    plural: 'Workflows',
    pluralLower: 'workflows',
    mineSubtitle:
      "Workflows you've uploaded or built in the Workflow Builder, including drafts that are still only visible to you.",
  },
};

/** The icon standing for each kind - on cards, in menus and in search results. */
export const KIND_ICONS: Record<ComponentKind, LucideIcon> = {
  tool: Package,
  workflow: Workflow,
};
