import type { Node } from '@xyflow/react';
import type { ParameterDisplayModel } from '@/api/components';

/**
 * Payload a sidebar card writes into the drag event - everything the canvas needs to
 * build a node, so a drop costs no request. The parameters come from the sidebar's own
 * list query, which opts into them via `includeParameters` (see WorkflowSidebar).
 */
export type ComponentDragPayload = {
  componentId: string;
  componentName: string;
  domains: string[];
  parameters: ParameterDisplayModel[];
};

export const DRAG_MIME = 'application/json';

/** Registered name of the custom edge that carries the delete button. */
export const COMPONENT_EDGE_TYPE = 'componentEdge';

export type ComponentNodeData = {
  componentId: string;
  label: string;
  domains: string[];
  /** drives the sidebar ranking and edge validation in lib/typeChecking.ts */
  parameters: ParameterDisplayModel[];
  /**
   * Values for the component's config parameters, keyed by parameter name and always
   * stored as strings (booleans as "true"/"false") to match ParameterDto.defaultValue.
   * A missing key means "unset" - the component's own default applies.
   */
  parameterValues: Record<string, string>;
};

export type ComponentFlowNode = Node<ComponentNodeData, 'componentNode'>;
