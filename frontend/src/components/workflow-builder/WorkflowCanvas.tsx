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
import { ComponentNode } from './ComponentNode';
import { DRAG_MIME, type ComponentDragPayload, type ComponentFlowNode } from './types';

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

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const raw = event.dataTransfer.getData(DRAG_MIME);
      if (!raw) return;

      // the sidebar's list query opts into `includeParameters`, so the drag payload
      // already carries the component's ports - no request needed to place a node
      const payload = JSON.parse(raw) as ComponentDragPayload;

      onAddNode({
        id: `${payload.componentId}-${Date.now()}`,
        type: 'componentNode',
        position: screenToFlowPosition({ x: event.clientX, y: event.clientY }),
        data: {
          componentId: payload.componentId,
          label: payload.componentName,
          domain: payload.domain,
          parameters: payload.parameters,
        },
      });
    },
    [screenToFlowPosition, onAddNode],
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
        deleteKeyCode={['Delete', 'Backspace']}
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#e2e8f0" />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}
