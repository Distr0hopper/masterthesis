import { useCallback } from 'react';
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  useReactFlow,
  type Edge,
  type OnConnect,
  type OnEdgesChange,
  type OnNodesChange,
} from '@xyflow/react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { componentKeys, componentTransformer, componentsService } from '@/api/components';
import { getErrorMessage } from '@/lib/errors';
import { ComponentNode } from './ComponentNode';
import { DRAG_MIME, type ComponentDragPayload, type ComponentFlowNode } from './types';

// module-level constants: re-creating either object on every render makes React Flow
// warn about a changed nodeTypes/edge config and re-mount every node
const nodeTypes = { componentNode: ComponentNode };
const defaultEdgeOptions = {
  type: 'smoothstep',
  style: { stroke: 'var(--jmu-blue-800)', strokeWidth: 1.5 },
  animated: false,
};

interface WorkflowCanvasProps {
  nodes: ComponentFlowNode[];
  edges: Edge[];
  onNodesChange: OnNodesChange<ComponentFlowNode>;
  onEdgesChange: OnEdgesChange<Edge>;
  onConnect: OnConnect;
  onAddNode: (node: ComponentFlowNode) => void;
}

export function WorkflowCanvas({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onAddNode,
}: WorkflowCanvasProps) {
  const { screenToFlowPosition } = useReactFlow();
  const queryClient = useQueryClient();

  const onDrop = useCallback(
    async (event: React.DragEvent) => {
      event.preventDefault();

      const raw = event.dataTransfer.getData(DRAG_MIME);
      if (!raw) return;

      const payload = JSON.parse(raw) as ComponentDragPayload;
      // resolved before the await - the event's clientX/Y are only valid synchronously
      const position = screenToFlowPosition({ x: event.clientX, y: event.clientY });

      try {
        // the list endpoint carries no parameters, so they are fetched per component here.
        // fetchQuery (not useComponent) because this is imperative, and it fills the very
        // same cache entry the detail page reads - a later navigation is already warm
        const detail = await queryClient.fetchQuery({
          queryKey: componentKeys.detail(payload.componentId),
          queryFn: () => componentsService.getById(payload.componentId),
        });

        onAddNode({
          id: `${payload.componentId}-${Date.now()}`,
          type: 'componentNode',
          position,
          data: {
            componentId: payload.componentId,
            label: payload.componentName,
            domain: payload.domain,
            // fetchQuery returns the raw DTO - a query's `select` does not apply to
            // imperative fetches, so the transform is applied by hand
            parameters: detail.parameters.map(componentTransformer.toParameterDisplayModel),
          },
        });
      } catch (error) {
        toast.error(getErrorMessage(error, 'Could not load this component.'));
      }
    },
    [screenToFlowPosition, queryClient, onAddNode],
  );

  return (
    <div
      className="h-full flex-1"
      onDrop={onDrop}
      onDragOver={(e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
      }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodeTypes={nodeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        fitView
        // Backspace included deliberately: on Mac keyboards the Delete key emits
        // Backspace, so "Delete" alone would make nodes undeletable there
        deleteKeyCode={['Delete', 'Backspace']}
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#e2e8f0" />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}
