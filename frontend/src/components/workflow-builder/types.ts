import type { Node } from '@xyflow/react';
import type { ParameterDisplayModel } from '@/api/components';

/**
 * Payload a sidebar card writes into the drag event. Deliberately smaller than
 * ComponentNodeData: the list endpoint (`ComponentListItemDto`) carries no parameters,
 * so the canvas fetches component detail on drop to fill them in.
 */
export type ComponentDragPayload = {
  componentId: string;
  componentName: string;
  domain: string;
};

/** MIME type used for the sidebar -> canvas drag transfer. */
export const DRAG_MIME = 'application/json';

// `type`, not `interface` - React Flow's Node<T> constrains T to Record<string, unknown>,
// and an interface gets no implicit index signature, so it would fail to satisfy that.
export type ComponentNodeData = {
  componentId: string;
  label: string;
  domain: string;
  /** carried but unrendered in AP 1 - AP 2 derives the real typed ports from these */
  parameters: ParameterDisplayModel[];
};

export type ComponentFlowNode = Node<ComponentNodeData, 'componentNode'>;
