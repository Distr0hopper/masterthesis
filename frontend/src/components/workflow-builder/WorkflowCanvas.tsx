import { useCallback, useEffect, useRef } from 'react';
import {
  Background,
  BackgroundVariant,
  ConnectionLineType,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlow,
  useNodesInitialized,
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

// jmu-blue-800. Inline `style` resolves CSS vars, but the arrow marker's colour lands on
// an SVG presentation attribute, where var() is not reliably resolved - hence the literal
// here, kept in sync with --jmu-blue-800 in index.css.
const EDGE_COLOR = '#093d79';

const defaultEdgeOptions = {
  // COMPONENT_EDGE_TYPE, not the built-in 'smoothstep' - the custom edge is what carries
  // the delete button. parseCanvasState normalises restored edges onto it too.
  type: COMPONENT_EDGE_TYPE,
  style: { stroke: EDGE_COLOR, strokeWidth: 2 },
  // an arrowhead is what makes a connection read as directional (output -> input)
  // rather than as an undirected line between two cards
  markerEnd: { type: MarkerType.ArrowClosed, color: EDGE_COLOR, width: 18, height: 18 },
  animated: false,
};

// the line that follows the cursor while dragging from a handle - the library default is
// a thin black stroke that reads as unrelated to the edges it creates
const connectionLineStyle = { stroke: EDGE_COLOR, strokeWidth: 2, strokeDasharray: '6 4' };

// a little breathing room around the graph, and a ceiling so a single small node does
// not get blown up to fill the viewport
const FIT_VIEW_OPTIONS = { padding: 0.2, maxZoom: 1.2 };

interface WorkflowCanvasProps {
  nodes: ComponentFlowNode[];
  edges: Edge[];
  onNodesChange: OnNodesChange<ComponentFlowNode>;
  onEdgesChange: OnEdgesChange<Edge>;
  onConnect: OnConnect;
  onAddNode: (node: ComponentFlowNode) => void;
  /**
   * Identifies the workflow currently open. Changing it re-fits the view once, after the
   * restored nodes have been measured.
   */
  fitViewKey: string;
}

export function WorkflowCanvas({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onAddNode,
  fitViewKey,
}: WorkflowCanvasProps) {
  const { screenToFlowPosition, fitView } = useReactFlow();

  // The `fitView` prop only fits on mount, and a saved workflow's nodes arrive later -
  // the draft query resolves after the canvas is already up, so that initial fit runs
  // against an empty canvas and the restored graph lands at whatever zoom it left behind.
  // useNodesInitialized goes true only once nodes have measured dimensions, which is what
  // fitView needs to compute a correct zoom.
  const nodesInitialized = useNodesInitialized();
  const fittedFor = useRef<string | null>(null);

  useEffect(() => {
    if (!nodesInitialized || nodes.length === 0) return;
    if (fittedFor.current === fitViewKey) return;

    // once per opened workflow - re-fitting on every later node drop would yank the
    // viewport around while the user is building
    fittedFor.current = fitViewKey;
    fitView(FIT_VIEW_OPTIONS);
  }, [nodesInitialized, nodes.length, fitViewKey, fitView]);

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
