import type { Node } from '@xyflow/react';
import type { ParameterDisplayModel } from '@/api/components';
import type { ConnectionCheckDto } from '@/api/compatibility';

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

/** Render-time data on a canvas edge - derived, never saved with a draft. */
export type ComponentEdgeData = {
  /** the backend's verdict - absent until it has answered */
  check?: ConnectionCheckDto;
};

/** Registered name of the custom edge that carries the delete button. */
export const COMPONENT_EDGE_TYPE = 'componentEdge';

export type ComponentNodeData = {
  componentId: string;
  label: string;
  domains: string[];
  /** drives the sidebar ranking and edge validation in lib/portKinds.ts */
  parameters: ParameterDisplayModel[];
  /**
   * Values for the component's config parameters, keyed by parameter name and always
   * stored as strings (booleans as "true"/"false") to match ParameterDto.defaultValue.
   * A missing key means "unset" - the component's own default applies.
   */
  parameterValues: Record<string, string>;
  /**
   * Render-time only: the component was deleted from the repository. Derived from the
   * draft's `missingComponentIds` on every render and never part of the page's node
   * state, so it can never end up in a saved draft.
   */
  missing?: boolean;
};

export type ComponentFlowNode = Node<ComponentNodeData, 'componentNode'>;
