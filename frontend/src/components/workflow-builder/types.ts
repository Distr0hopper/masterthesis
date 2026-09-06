import type { Node } from '@xyflow/react';
import type { ParameterDisplayModel } from '@/api/components';

/**
 * TODO: Check if we can use Parameters directly
 * Payload a sidebar card writes into the drag event. Deliberately smaller than
 * ComponentNodeData: the list endpoint (`ComponentListItemDto`) carries no parameters,
 * so the canvas fetches component detail on drop to fill them in.
 */
export type ComponentDragPayload = {
  componentId: string;
  componentName: string;
  domain: string;
};

export const DRAG_MIME = 'application/json';

export type ComponentNodeData = {
  componentId: string;
  label: string;
  domain: string;
  /** carried but unrendered in AP 1 - AP 2 derives the real typed ports from these */
  parameters: ParameterDisplayModel[];
};

export type ComponentFlowNode = Node<ComponentNodeData, 'componentNode'>;
