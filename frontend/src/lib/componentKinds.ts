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
}

export const KIND_COPY: Record<ComponentKind, KindCopy> = {
  tool: {
    singular: 'Tool',
    plural: 'Tools',
    pluralLower: 'tools',
  },
  workflow: {
    singular: 'Workflow',
    plural: 'Workflows',
    pluralLower: 'workflows',
  },
};

/** Every kind, in the order lists and filters show them. */
export const KINDS = Object.keys(KIND_COPY) as ComponentKind[];

/** `value` as a kind, or undefined when it is none - for kinds read from the URL. */
export function parseKind(value: string | null): ComponentKind | undefined {
  return KINDS.find((kind) => kind === value);
}

/** The icon standing for each kind - on cards, in menus and in search results. */
export const KIND_ICONS: Record<ComponentKind, LucideIcon> = {
  tool: Package,
  workflow: Workflow,
};
