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
  domain: string;
  parameters: ParameterDisplayModel[];
};

export const DRAG_MIME = 'application/json';

/** Registered name of the custom edge that carries the delete button. */
export const COMPONENT_EDGE_TYPE = 'componentEdge';

export type ComponentNodeData = {
  componentId: string;
  label: string;
  domain: string;
  /** drives the sidebar ranking and edge validation in lib/typeChecking.ts */
  parameters: ParameterDisplayModel[];
};

export type ComponentFlowNode = Node<ComponentNodeData, 'componentNode'>;
