import { useCallback, useMemo } from 'react';
import {
  Background,
  BackgroundVariant,
  ConnectionLineType,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlow,
  useReactFlow,
  type Edge,
  type OnConnect,
  type OnEdgesChange,
  type OnNodesChange,
} from '@xyflow/react';
import { ComponentEdge } from './ComponentEdge';
import { ComponentNode } from './ComponentNode';
import { COMPONENT_EDGE_TYPE, DRAG_MIME, type ComponentDragPayload, type ComponentFlowNode } from './types';

const nodeTypes = { componentNode: ComponentNode };
const edgeTypes = { componentEdge: ComponentEdge };

// a little breathing room around the graph, and a ceiling so a single small node does
// not get blown up to fill the viewport
const FIT_VIEW_OPTIONS = { padding: 0.2, maxZoom: 1.2 };

function readBrandBlue(): string {
  return getComputedStyle(document.documentElement).getPropertyValue('--jmu-blue-800').trim();
}

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

  // read once - the brand palette does not change at runtime
  const brandBlue = useMemo(readBrandBlue, []);

  const defaultEdgeOptions = useMemo(
    () => ({
      // COMPONENT_EDGE_TYPE, not the built-in 'smoothstep' - the custom edge is what
      // carries the delete button. parseCanvasState normalises restored edges onto it too.
      type: COMPONENT_EDGE_TYPE,
      style: { stroke: brandBlue, strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: brandBlue, width: 18, height: 18 },
      animated: false,
    }),
    [brandBlue],
  );

  const connectionLineStyle = useMemo(
    () => ({ stroke: brandBlue, strokeWidth: 2, strokeDasharray: '6 4' }),
    [brandBlue],
  );

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const raw = event.dataTransfer.getData(DRAG_MIME);
      if (!raw) return;

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
          // no overrides yet - every config parameter starts on its component default
          parameterValues: {},
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
        edgeTypes={edgeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        connectionLineType={ConnectionLineType.SmoothStep}
        connectionLineStyle={connectionLineStyle}
        // widens the grab area around each handle without drawing a bigger dot
        connectionRadius={30}
        // The page defers mounting this component until a restored workflow's nodes are in
        // state (see WorkflowBuilderPage), so React Flow's own one-shot fitView runs once
        // the nodes have been measured and frames the whole graph.
        fitView
        fitViewOptions={FIT_VIEW_OPTIONS}
        deleteKeyCode={['Delete', 'Backspace']}
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#e2e8f0" />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}
