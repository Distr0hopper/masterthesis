import { ComponentSource, type ComponentKind } from '@/api/components/types';

/** The sources each kind can come from - a tool is never built in the builder, a workflow never packaged. */
export const SOURCES_BY_KIND: Record<ComponentKind, readonly ComponentSource[]> = {
  tool: [ComponentSource.AUTOMATED_PACKAGING, ComponentSource.MANUAL_UPLOAD],
  workflow: [ComponentSource.WORKFLOW_BUILDER, ComponentSource.MANUAL_UPLOAD],
};

/** Every source, in the order filters show them. */
export const SOURCE_ORDER = [
  ComponentSource.AUTOMATED_PACKAGING,
  ComponentSource.WORKFLOW_BUILDER,
  ComponentSource.MANUAL_UPLOAD,
] as const;

/** The sources worth offering for a kind - all of them while no kind is chosen. */
export function sourcesFor(kind: ComponentKind | undefined): readonly ComponentSource[] {
  return kind ? SOURCE_ORDER.filter((source) => SOURCES_BY_KIND[kind].includes(source)) : SOURCE_ORDER;
}

/** `value` as a source, or undefined when it is none - for sources read from the URL. */
export function parseSource(value: string | null): ComponentSource | undefined {
  return SOURCE_ORDER.find((source) => source === value);
}
